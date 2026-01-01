"""
Authentication Blueprint - handles Google OAuth login/logout
"""
import json
import os
import time
from datetime import datetime

from authlib.integrations.flask_client import OAuth
from flask import Blueprint, current_app, flash, redirect, request, session, url_for
from flask_login import current_user, login_required, login_user, logout_user

from extensions import db
from models import SharedTitle, User

auth_bp = Blueprint("auth", __name__, url_prefix="/auth")

# Initialize OAuth
oauth = OAuth()


def init_oauth(app):
    """Initialize OAuth with app"""
    client_id = os.getenv("GOOGLE_CLIENT_ID")
    client_secret = os.getenv("GOOGLE_CLIENT_SECRET")

    secrets_path = os.getenv("GOOGLE_CLIENT_SECRETS_FILE")
    if secrets_path and os.path.exists(secrets_path):
        try:
            with open(secrets_path, "r", encoding="utf-8") as fh:
                data = json.load(fh)
            config = data.get("web") or data.get("installed") or {}
            client_id = config.get("client_id", client_id)
            client_secret = config.get("client_secret", client_secret)
        except Exception:
            app.logger.warning(
                "Failed to load Google client secrets file; falling back to env vars"
            )

    oauth.init_app(app)

    def save_token(token, refresh_token=None, access_token=None):
        """Persist refreshed tokens when Authlib refreshes in-session."""
        try:
            if current_user and current_user.is_authenticated:
                current_user.oauth_token = json.dumps(token)
                db.session.commit()
        except Exception:
            # Avoid breaking flow if commit fails
            app.logger.warning("Failed to persist refreshed OAuth token")

    oauth.register(
        name="google",
        client_id=client_id,
        client_secret=client_secret,
        server_metadata_url="https://accounts.google.com/.well-known/openid-configuration",
        client_kwargs={
            "scope": "openid email profile https://www.googleapis.com/auth/calendar"
        },
        update_token=save_token,
    )


def get_google_token_for_user(user, logger=None):
    """Return a valid Google token for the user; attempt refresh if expired.

    Returns None if no usable token is available.
    """
    if not user:
        return None

    token = getattr(user, "get_oauth_token", lambda: None)()
    if not token:
        return None

    try:
        expires_at = token.get("expires_at")
        refresh_token = token.get("refresh_token")
        now = time.time()

        # If token is expired or expiring within 60s, try to refresh
        if expires_at and expires_at - now <= 60 and refresh_token:
            # Get token endpoint from well-known config
            token_endpoint = "https://oauth2.googleapis.com/token"
            new_token = oauth.google.fetch_access_token(
                grant_type="refresh_token",
                refresh_token=refresh_token,
            )
            # Persist refreshed token
            user.set_oauth_token(new_token)
            token = new_token

    except Exception as exc:
        log = logger or current_app.logger
        log.warning(
            f'Failed to refresh Google token for user {getattr(user, "id", "?")}: {exc}'
        )
        return None

    return token


@auth_bp.route("/login")
def login():
    """Redirect to Google OAuth login"""
    # Prefer explicit override, otherwise derive from current request host to keep session state aligned.
    redirect_uri = os.getenv("GOOGLE_REDIRECT_URI")
    if not redirect_uri:
        redirect_uri = url_for("auth.callback", _external=True, _scheme=request.scheme)
    # Preserve next page if provided (so we can redirect after login)
    next_arg = request.args.get("next")
    if next_arg:
        session["next"] = next_arg
    # Request offline access to obtain refresh_token
    # Note: prompt="consent" forces consent screen every time (needed for refresh_token)
    # We only force it on first login or explicit re-auth
    force_consent = request.args.get("reauth") == "1"
    if force_consent:
        return oauth.google.authorize_redirect(
            redirect_uri, prompt="consent", access_type="offline"
        )
    return oauth.google.authorize_redirect(redirect_uri, access_type="offline")


@auth_bp.route("/callback")
def callback():
    """Handle Google OAuth callback"""
    try:
        token = oauth.google.authorize_access_token()
        user_info = token.get("userinfo")
        access_token = token.get("access_token")

        if not user_info:
            flash("Failed to get user info from Google", "error")
            return redirect(url_for("index"))

        # Check if user exists by google_id OR email
        user = User.query.filter_by(google_id=user_info["sub"]).first()
        if not user:
            user = User.query.filter_by(email=user_info["email"]).first()

        if not user:
            # Create new user
            user = User(
                google_id=user_info["sub"],
                email=user_info["email"],
                name=user_info.get("name"),
                profile_pic=user_info.get("picture"),
                role="user",  # Default role
                created_at=datetime.utcnow(),
                oauth_token=json.dumps(token),
            )
            db.session.add(user)
            db.session.commit()

            # Seed default shared titles for new user
            SharedTitle.seed_for_user(user.id)
        else:
            # Update existing user with OAuth info
            user.google_id = user_info["sub"]
            user.last_login = datetime.utcnow()
            user.name = user_info.get("name", user.name)
            user.profile_pic = user_info.get("picture", user.profile_pic)
            # Preserve existing refresh_token if new token doesn't have one
            # (happens when logging in without prompt="consent")
            if token.get("refresh_token"):
                user.oauth_token = json.dumps(token)
            elif user.oauth_token:
                # Keep existing token's refresh_token, update access_token
                existing_token = user.get_oauth_token()
                if existing_token and existing_token.get("refresh_token"):
                    token["refresh_token"] = existing_token["refresh_token"]
                    user.oauth_token = json.dumps(token)
        db.session.commit()

        # Log user in
        login_user(user)
        # Clear any queued flash messages from redirects (e.g., login_required prompts)
        session.pop("_flashes", None)
        # Show a single success message
        flash(f"Welcome back, {user.name}!", "success")

        # Redirect to next page or home
        next_page = session.get("next")
        if next_page:
            session.pop("next")
            return redirect(next_page)

        return redirect(url_for("index"))

    except Exception as e:
        flash(f"Authentication error: {str(e)}", "error")
        return redirect(url_for("index"))


@auth_bp.route("/logout")
@login_required
def logout():
    """Logout user"""
    logout_user()
    flash("You have been logged out.", "success")
    return redirect(url_for("index"))


@auth_bp.route("/settings", methods=["GET", "POST"])
@login_required
def settings():
    """User settings page - configure calendar options"""
    from flask import render_template

    if request.method == "POST":
        # Update shared calendar ID
        shared_calendar_id = request.form.get("shared_calendar_id", "").strip()

        # Basic validation - should look like an email or calendar ID
        if shared_calendar_id and "@" not in shared_calendar_id:
            flash(
                "Invalid calendar ID format. Should be an email-like address.", "error"
            )
            return redirect(url_for("auth.settings"))

        current_user.shared_calendar_id = (
            shared_calendar_id if shared_calendar_id else None
        )
        db.session.commit()

        flash("Settings saved successfully!", "success")
        return redirect(url_for("auth.settings"))

    # Get user's shared titles for display/management
    shared_titles = (
        SharedTitle.query.filter_by(user_id=current_user.id)
        .order_by(SharedTitle.position)
        .all()
    )

    return render_template(
        "auth/settings.html",
        shared_calendar_id=current_user.shared_calendar_id or "",
        shared_titles=shared_titles,
    )


@auth_bp.route("/settings/titles", methods=["POST"])
@login_required
def update_shared_titles():
    """Update user's shared calendar titles"""
    action = request.form.get("action")

    if action == "add":
        title = request.form.get("title", "").strip()
        if title:
            # Get max position
            max_pos = (
                db.session.query(db.func.max(SharedTitle.position))
                .filter_by(user_id=current_user.id)
                .scalar()
                or 0
            )

            new_title = SharedTitle(
                user_id=current_user.id,
                title=title,
                is_default_work_hours=False,
                position=max_pos + 1,
            )
            db.session.add(new_title)
            db.session.commit()
            flash(f"Added title: {title}", "success")
        else:
            flash("Title cannot be empty", "error")

    elif action == "delete":
        title_id = request.form.get("title_id")
        if title_id:
            title_obj = SharedTitle.query.filter_by(
                id=title_id, user_id=current_user.id
            ).first()
            if title_obj:
                db.session.delete(title_obj)
                db.session.commit()
                flash(f"Deleted title: {title_obj.title}", "success")

    elif action == "toggle_default":
        title_id = request.form.get("title_id")
        if title_id:
            title_obj = SharedTitle.query.filter_by(
                id=title_id, user_id=current_user.id
            ).first()
            if title_obj:
                title_obj.is_default_work_hours = not title_obj.is_default_work_hours
                db.session.commit()
                status = "default" if title_obj.is_default_work_hours else "not default"
                flash(f"'{title_obj.title}' is now {status} for work hours", "info")

    return redirect(url_for("auth.settings"))


# Development Mode Routes
@auth_bp.route("/dev/login", methods=["GET", "POST"])
def dev_login():
    """Development mode: Simple login form"""
    if os.getenv("DEVELOPMENT_MODE", "False").lower() != "true":
        flash("Development mode is not enabled.", "error")
        return redirect(url_for("auth.login"))

    if request.method == "POST":
        user_id = request.form.get("user_id")
        if user_id:
            user = db.session.get(User, int(user_id))
            if user:
                user.last_login = datetime.utcnow()
                db.session.commit()
                login_user(user)
                flash(f"Logged in as {user.name} ({user.role})", "success")
                return redirect(url_for("index"))
        flash("Invalid user selection.", "error")

    # Get all users for selection
    users = User.query.order_by(User.email).all()
    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Development Login - Orbis</title>
        <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css" rel="stylesheet">
    </head>
    <body>
        <div class="container mt-5">
            <div class="row justify-content-center">
                <div class="col-md-6">
                    <div class="card">
                        <div class="card-header bg-warning text-dark">
                            <h4>🔧 Development Mode Login</h4>
                        </div>
                        <div class="card-body">
                            <div class="alert alert-warning">
                                <strong>⚠️ Development Mode Only</strong><br>
                                This login method bypasses OAuth. Set DEVELOPMENT_MODE=False in .env for production.
                            </div>
                            <form method="POST">
                                <div class="mb-3">
                                    <label class="form-label">Select User:</label>
                                    <select name="user_id" class="form-select" required>
                                        <option value="">Choose a user...</option>
                                        {''.join([f'<option value="{u.id}">{u.name} ({u.email}) - {u.role.upper()}</option>' for u in users])}
                                    </select>
                                </div>
                                <button type="submit" class="btn btn-primary w-100">Login</button>
                            </form>
                            <hr>
                            <div class="d-grid gap-2">
                                <a href="{url_for('auth.dev_create_user')}" class="btn btn-outline-secondary">+ Create New User</a>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    </body>
    </html>
    """


@auth_bp.route("/dev/create", methods=["GET", "POST"])
def dev_create_user():
    """Development mode: Create a test user"""
    if os.getenv("DEVELOPMENT_MODE", "False").lower() != "true":
        flash("Development mode is not enabled.", "error")
        return redirect(url_for("auth.login"))

    if request.method == "POST":
        email = request.form.get("email")
        name = request.form.get("name")
        role = request.form.get("role", "user")

        if not email or not name:
            return '<script>alert("Email and name required!"); history.back();</script>'

        # Check if user exists
        existing = User.query.filter_by(email=email).first()
        if existing:
            return '<script>alert("User with this email already exists!"); history.back();</script>'

        user = User(
            google_id=f"dev_{email}",
            email=email,
            name=name,
            role=role,
            created_at=datetime.utcnow(),
        )
        db.session.add(user)
        db.session.commit()

        flash(f"Created user: {name} ({role})", "success")
        return redirect(url_for("auth.dev_login"))

    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Create User - Orbis</title>
        <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css" rel="stylesheet">
    </head>
    <body>
        <div class="container mt-5">
            <div class="row justify-content-center">
                <div class="col-md-6">
                    <div class="card">
                        <div class="card-header">
                            <h4>Create Test User</h4>
                        </div>
                        <div class="card-body">
                            <form method="POST">
                                <div class="mb-3">
                                    <label class="form-label">Name:</label>
                                    <input type="text" name="name" class="form-control" required>
                                </div>
                                <div class="mb-3">
                                    <label class="form-label">Email:</label>
                                    <input type="email" name="email" class="form-control" required>
                                </div>
                                <div class="mb-3">
                                    <label class="form-label">Role:</label>
                                    <select name="role" class="form-select">
                                        <option value="user">User</option>
                                        <option value="admin">Admin</option>
                                    </select>
                                </div>
                                <button type="submit" class="btn btn-primary w-100">Create User</button>
                            </form>
                            <hr>
                            <a href="{url_for('auth.dev_login')}" class="btn btn-outline-secondary w-100">Back to Login</a>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    </body>
    </html>
    """
