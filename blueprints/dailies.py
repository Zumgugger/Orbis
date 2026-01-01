"""
Dailies Blueprint - handles recurring daily tasks
"""
from datetime import date, datetime, timedelta

from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from extensions import db
from models import CompletionLog, Daily, sync_entity_tags
from validation import (
    ValidationError,
    validate_frequency,
    validate_integer,
    validate_text,
    validate_title,
    validate_weekdays,
)


def _parse_tag_ids(form_value: str) -> list[int]:
    """Parse comma-separated tag IDs from form input."""
    if not form_value:
        return []
    return [int(tid) for tid in form_value.split(",") if tid.strip().isdigit()]


dailies_bp = Blueprint("dailies", __name__, url_prefix="/dailies")

WEEKDAYS = [
    "monday",
    "tuesday",
    "wednesday",
    "thursday",
    "friday",
    "saturday",
    "sunday",
]


@dailies_bp.route("/")
@login_required
def list_dailies():
    """Display all dailies"""
    dailies = (
        Daily.query.filter_by(user_id=current_user.id)
        .order_by(Daily.created_at.desc())
        .all()
    )
    return render_template("dailies/list.html", dailies=dailies, weekdays=WEEKDAYS)


@dailies_bp.route("/create", methods=["GET", "POST"])
@login_required
def create_daily():
    """Create a new daily"""
    if request.method == "POST":
        try:
            title = validate_title(request.form.get("title"), max_length=200)
            description = validate_text(
                request.form.get("description"), max_length=5000
            )
            frequency = validate_frequency(request.form.get("frequency"))
            frequency_interval = (
                validate_integer(
                    request.form.get("frequency_interval"), min_val=1, max_val=365
                )
                or 1
            )

            daily = Daily(
                title=title,
                description=description,
                frequency=frequency,
                frequency_interval=frequency_interval,
                user_id=current_user.id,
            )

            # Handle custom weekdays
            if frequency == "custom":
                selected_weekdays = validate_weekdays(
                    request.form.getlist("weekdays"), required=True
                )
                daily.set_weekdays(selected_weekdays)

            db.session.add(daily)
            db.session.commit()

            flash("Daily created successfully!", "success")
            return redirect(url_for("dailies.list_dailies"))
        except ValidationError as e:
            flash(str(e), "error")
            return render_template(
                "dailies/form.html", daily=None, action="Create", weekdays=WEEKDAYS
            )

    return render_template(
        "dailies/form.html", daily=None, action="Create", weekdays=WEEKDAYS
    )


@dailies_bp.route("/<int:daily_id>/edit", methods=["GET", "POST"])
@login_required
def edit_daily(daily_id):
    """Edit an existing daily"""
    daily = Daily.query.filter_by(id=daily_id, user_id=current_user.id).first_or_404()

    if request.method == "POST":
        try:
            daily.title = validate_title(request.form.get("title"), max_length=200)
            daily.description = validate_text(
                request.form.get("description"), max_length=5000
            )
            daily.frequency = validate_frequency(request.form.get("frequency"))
            daily.frequency_interval = (
                validate_integer(
                    request.form.get("frequency_interval"), min_val=1, max_val=365
                )
                or 1
            )

            # Handle custom weekdays
            if daily.frequency == "custom":
                selected_weekdays = validate_weekdays(
                    request.form.getlist("weekdays"), required=True
                )
                daily.set_weekdays(selected_weekdays)
            else:
                daily.weekdays = None

            # Sync tags
            tag_ids = _parse_tag_ids(request.form.get("tag_ids", ""))
            sync_entity_tags(current_user.id, "daily", daily.id, tag_ids)

            db.session.commit()
            flash("Daily updated successfully!", "success")
            return redirect(url_for("dailies.list_dailies"))
        except ValidationError as e:
            flash(str(e), "error")
            return render_template(
                "dailies/form.html", daily=daily, action="Edit", weekdays=WEEKDAYS
            )

    return render_template(
        "dailies/form.html", daily=daily, action="Edit", weekdays=WEEKDAYS
    )


@dailies_bp.route("/<int:daily_id>/toggle", methods=["POST"])
@login_required
def toggle_daily(daily_id):
    """Toggle daily completion status"""
    daily = Daily.query.filter_by(id=daily_id, user_id=current_user.id).first_or_404()

    if not daily.should_complete_today():
        frequency_name = daily.frequency.capitalize()
        flash(
            f"This daily is not available today. It is set to {frequency_name}.",
            "warning",
        )
        next_page = request.args.get("next")
        if next_page:
            return redirect(next_page)
        return redirect(url_for("dailies.list_dailies"))

    daily.toggle_completion()
    db.session.commit()
    next_page = request.args.get("next")
    if next_page:
        return redirect(next_page)
    return redirect(url_for("dailies.list_dailies"))


@dailies_bp.route("/<int:daily_id>/delete", methods=["POST"])
@login_required
def delete_daily(daily_id):
    """Delete a daily"""
    daily = Daily.query.filter_by(id=daily_id, user_id=current_user.id).first_or_404()
    db.session.delete(daily)
    db.session.commit()
    flash("Daily deleted successfully!", "success")
    return redirect(url_for("dailies.list_dailies"))


@dailies_bp.route("/<int:daily_id>/toggle_for_date", methods=["POST"])
@login_required
def toggle_for_date(daily_id):
    """Toggle completion for a specific date (used on Tomorrow). Disabled for daily frequency."""
    daily = Daily.query.filter_by(id=daily_id, user_id=current_user.id).first_or_404()
    target_date_str = request.form.get("target_date")
    next_page = request.args.get("next") or request.form.get("next")
    if not target_date_str:
        flash("No target date provided.", "error")
        return redirect(next_page or url_for("dailies.list_dailies"))
    try:
        target_date = datetime.strptime(target_date_str, "%Y-%m-%d").date()
    except ValueError:
        flash("Invalid target date.", "error")
        return redirect(next_page or url_for("dailies.list_dailies"))

    if daily.frequency == "daily":
        flash("Daily repetition cannot be scratched early.", "warning")
        return redirect(next_page or url_for("dailies.list_dailies"))

    daily.toggle_completion_on(target_date)
    db.session.commit()

    if next_page:
        return redirect(next_page)
    return redirect(url_for("dailies.list_dailies"))


@dailies_bp.route("/reorder", methods=["POST"])
@login_required
def reorder():
    """Persist drag-and-drop order of dailies for the current user"""
    payload = request.get_json(silent=True) or {}
    order = payload.get("order", [])
    if not isinstance(order, list):
        return {"success": False, "error": "Invalid order payload"}, 400

    try:
        for position, daily_id in enumerate(order):
            daily = Daily.query.filter_by(id=daily_id, user_id=current_user.id).first()
            if daily:
                daily.position = position
        db.session.commit()
        return {"success": True}, 200
    except Exception:
        db.session.rollback()
        return {"success": False, "error": "Failed to persist order"}, 500


# ---- Yesterday's Dailies (Complete for past date) ----
@dailies_bp.route("/<int:daily_id>/complete_yesterday", methods=["POST"])
@login_required
def complete_yesterday(daily_id):
    """Mark a daily as complete for yesterday"""
    daily = Daily.query.filter_by(id=daily_id, user_id=current_user.id).first_or_404()
    yesterday = date.today() - timedelta(days=1)

    if not daily.should_complete_on(yesterday):
        flash("This daily was not scheduled for yesterday.", "warning")
        return redirect(request.referrer or url_for("index"))

    if daily.is_completed_on(yesterday):
        flash("Already completed for yesterday.", "info")
        return redirect(request.referrer or url_for("index"))

    # Complete for yesterday
    daily.toggle_completion_on(yesterday)

    # Log completion
    log = CompletionLog(
        user_id=current_user.id,
        item_type="daily",
        item_id=daily.id,
        title_snapshot=daily.title,
        description_snapshot=daily.description,
        completed_date=yesterday,
    )
    db.session.add(log)
    db.session.commit()

    flash(f"'{daily.title}' marked complete for yesterday!", "success")
    return redirect(request.referrer or url_for("index"))


@dailies_bp.route("/dismiss_yesterday", methods=["POST"])
@login_required
def dismiss_yesterday():
    """Dismiss the yesterday's dailies popup and break streaks"""

    yesterday = date.today() - timedelta(days=1)
    dailies = Daily.query.filter_by(user_id=current_user.id).all()

    for daily in dailies:
        if daily.should_complete_on(yesterday) and not daily.is_completed_on(yesterday):
            # Break streak
            daily.streak_count = 0

    db.session.commit()
    flash("Yesterday's missed dailies dismissed. Streaks reset.", "info")
    return redirect(url_for("index"))


# ---- Streak Freeze ----
@dailies_bp.route("/<int:daily_id>/use_freeze", methods=["POST"])
@login_required
def use_streak_freeze(daily_id):
    """Use a streak freeze to preserve streak for a missed daily"""
    daily = Daily.query.filter_by(id=daily_id, user_id=current_user.id).first_or_404()

    if not daily.can_use_streak_freeze():
        if daily.streak_count == 0:
            flash("No streak to preserve.", "warning")
        else:
            flash("No streak freezes remaining this month.", "warning")
        return redirect(request.referrer or url_for("dailies.list_dailies"))

    if daily.use_streak_freeze():
        db.session.commit()
        remaining = daily.get_freezes_remaining()
        flash(
            f"Streak freeze used for '{daily.title}'! {remaining} freeze(s) remaining this month.",
            "success",
        )
    else:
        flash("Could not use streak freeze.", "error")

    return redirect(request.referrer or url_for("dailies.list_dailies"))


# ---- History & Stats ----
@dailies_bp.route("/history")
@login_required
def history():
    """Show completion history calendar and stats"""
    # Get all dailies
    dailies = (
        Daily.query.filter_by(user_id=current_user.id)
        .order_by(Daily.position.asc(), Daily.id.asc())
        .all()
    )

    # Get completion logs for last 90 days
    ninety_days_ago = date.today() - timedelta(days=90)
    logs = (
        CompletionLog.query.filter(
            CompletionLog.user_id == current_user.id,
            CompletionLog.item_type == "daily",
            CompletionLog.completed_date >= ninety_days_ago,
        )
        .order_by(CompletionLog.completed_date.desc())
        .all()
    )

    # Build calendar data (last 35 days for 5-week view)
    today = date.today()
    calendar_days = []
    for i in range(34, -1, -1):
        d = today - timedelta(days=i)
        calendar_days.append(d)

    # Map logs by date
    completion_map = {}
    for log in logs:
        d = log.completed_date
        if d not in completion_map:
            completion_map[d] = []
        completion_map[d].append(log)

    # Calculate stats
    # Weekly (last 7 days)
    week_ago = today - timedelta(days=7)
    week_completions = sum(1 for log in logs if log.completed_date > week_ago)
    week_expected = 0
    for daily in dailies:
        for i in range(7):
            d = today - timedelta(days=i)
            if daily.should_complete_on(d):
                week_expected += 1
    week_rate = (
        int((week_completions / week_expected) * 100) if week_expected > 0 else 0
    )

    # Monthly (last 30 days)
    month_ago = today - timedelta(days=30)
    month_completions = sum(1 for log in logs if log.completed_date > month_ago)
    month_expected = 0
    for daily in dailies:
        for i in range(30):
            d = today - timedelta(days=i)
            if daily.should_complete_on(d):
                month_expected += 1
    month_rate = (
        int((month_completions / month_expected) * 100) if month_expected > 0 else 0
    )

    # Best streaks
    best_streaks = sorted(dailies, key=lambda d: d.best_streak or 0, reverse=True)[:5]

    return render_template(
        "dailies/history.html",
        dailies=dailies,
        calendar_days=calendar_days,
        completion_map=completion_map,
        week_completions=week_completions,
        week_expected=week_expected,
        week_rate=week_rate,
        month_completions=month_completions,
        month_expected=month_expected,
        month_rate=month_rate,
        best_streaks=best_streaks,
        today=today,
    )
