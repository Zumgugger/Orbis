"""
Habits Blueprint - handles habit tracking with +/- counters
"""
from collections import defaultdict
from datetime import date, datetime, timedelta

from flask import Blueprint, flash, jsonify, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from extensions import db
from models import Habit, HabitLog, sync_entity_tags
from validation import (
    ValidationError,
    validate_difficulty,
    validate_text,
    validate_title,
)


def _parse_tag_ids(form_value: str) -> list[int]:
    """Parse comma-separated tag IDs from form input."""
    if not form_value:
        return []
    return [int(tid) for tid in form_value.split(",") if tid.strip().isdigit()]


habits_bp = Blueprint("habits", __name__, url_prefix="/habits")


@habits_bp.route("/")
@login_required
def list_habits():
    """Display all habits"""
    habits = (
        Habit.query.filter_by(user_id=current_user.id)
        .order_by(Habit.position.asc(), Habit.id.asc())
        .all()
    )
    return render_template("habits/list.html", habits=habits)


@habits_bp.route("/create", methods=["GET", "POST"])
@login_required
def create_habit():
    """Create a new habit"""
    if request.method == "POST":
        try:
            title = validate_title(request.form.get("title"), max_length=200)
            description = validate_text(
                request.form.get("description"), max_length=5000
            )
            difficulty = validate_difficulty(request.form.get("difficulty"))

            habit = Habit(
                title=title,
                description=description,
                difficulty=difficulty,
                user_id=current_user.id,
            )
            db.session.add(habit)
            db.session.flush()  # Get habit.id for tag syncing

            # Sync tags
            tag_ids = _parse_tag_ids(request.form.get("tag_ids", ""))
            sync_entity_tags(current_user.id, "habit", habit.id, tag_ids)

            db.session.commit()

            flash("Habit created successfully!", "success")
            return redirect(url_for("habits.list_habits"))
        except ValidationError as e:
            flash(str(e), "error")
            return render_template("habits/form.html", habit=None, action="Create")

    return render_template("habits/form.html", habit=None, action="Create")


@habits_bp.route("/<int:habit_id>/edit", methods=["GET", "POST"])
@login_required
def edit_habit(habit_id):
    """Edit an existing habit"""
    habit = Habit.query.filter_by(id=habit_id, user_id=current_user.id).first_or_404()

    if request.method == "POST":
        try:
            habit.title = validate_title(request.form.get("title"), max_length=200)
            habit.description = validate_text(
                request.form.get("description"), max_length=5000
            )
            habit.difficulty = validate_difficulty(request.form.get("difficulty"))

            # Sync tags
            tag_ids = _parse_tag_ids(request.form.get("tag_ids", ""))
            sync_entity_tags(current_user.id, "habit", habit.id, tag_ids)

            db.session.commit()
            flash("Habit updated successfully!", "success")
            return redirect(url_for("habits.list_habits"))
        except ValidationError as e:
            flash(str(e), "error")
            return render_template("habits/form.html", habit=habit, action="Edit")

    return render_template("habits/form.html", habit=habit, action="Edit")


@habits_bp.route("/<int:habit_id>/increment", methods=["POST"])
@login_required
def increment_habit(habit_id):
    """Increment habit count (+1)"""
    habit = Habit.query.filter_by(id=habit_id, user_id=current_user.id).first_or_404()

    is_ajax = (
        request.headers.get("X-Requested-With") == "XMLHttpRequest" or request.is_json
    )

    target_date = None
    if is_ajax:
        data = request.get_json(silent=True) or {}
        target_date_str = data.get("target_date") or request.form.get("target_date")
    else:
        target_date_str = request.form.get("target_date")

    if target_date_str:
        try:
            target_date = datetime.strptime(target_date_str, "%Y-%m-%d").date()
        except ValueError:
            target_date = None

    habit.increment(target_date=target_date)
    db.session.commit()

    if is_ajax:
        return jsonify(
            {
                "success": True,
                "count": habit.count,
                "last_increment_date": habit.last_increment_date.isoformat()
                if habit.last_increment_date
                else None,
            }
        )

    next_page = request.args.get("next") or request.form.get("next")
    if next_page:
        return redirect(next_page)
    return redirect(url_for("habits.list_habits"))


@habits_bp.route("/<int:habit_id>/decrement", methods=["POST"])
@login_required
def decrement_habit(habit_id):
    """Decrement habit count (-1)"""
    habit = Habit.query.filter_by(id=habit_id, user_id=current_user.id).first_or_404()
    habit.decrement()
    db.session.commit()
    return redirect(url_for("habits.list_habits"))


@habits_bp.route("/<int:habit_id>/cycle_difficulty", methods=["POST"])
@login_required
def cycle_difficulty(habit_id):
    """Cycle through difficulty levels: easy -> normal -> hard -> easy"""
    habit = Habit.query.filter_by(id=habit_id, user_id=current_user.id).first_or_404()

    if habit.difficulty == "easy":
        habit.difficulty = "normal"
    elif habit.difficulty == "normal":
        habit.difficulty = "hard"
    else:  # hard
        habit.difficulty = "easy"

    db.session.commit()
    return redirect(url_for("habits.list_habits"))


@habits_bp.route("/reorder", methods=["POST"])
@login_required
def reorder_habits():
    """Persist new habit order from drag-and-drop"""
    try:
        data = request.get_json(silent=True) or {}
        ids = data.get("order", [])

        if not isinstance(ids, list):
            return (
                jsonify(
                    {"error": "Invalid payload", "message": "Order must be a list"}
                ),
                400,
            )

        # Filter to user's habits only
        user_habits = Habit.query.filter_by(user_id=current_user.id).all()
        user_ids = {h.id for h in user_habits}
        filtered = [hid for hid in ids if hid in user_ids]

        for idx, hid in enumerate(filtered):
            Habit.query.filter_by(id=hid, user_id=current_user.id).update(
                {"position": idx}
            )

        db.session.commit()
        return jsonify({"status": "ok"})
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": "Failed to reorder", "message": str(e)}), 500


@habits_bp.route("/<int:habit_id>/focus", methods=["POST"])
@login_required
def toggle_focus(habit_id):
    """Toggle focused flag for habit"""
    habit = Habit.query.filter_by(id=habit_id, user_id=current_user.id).first_or_404()
    habit.focused = not habit.focused
    db.session.commit()
    return redirect(url_for("habits.list_habits"))


@habits_bp.route("/<int:habit_id>/delete", methods=["POST"])
@login_required
def delete_habit(habit_id):
    """Delete a habit"""
    habit = Habit.query.filter_by(id=habit_id, user_id=current_user.id).first_or_404()
    db.session.delete(habit)
    db.session.commit()
    flash("Habit deleted successfully!", "success")
    return redirect(url_for("habits.list_habits"))


@habits_bp.route("/insights")
@login_required
def insights():
    """Display habit insights, trends, and history"""
    today = date.today()

    # Get all user habits
    habits = (
        Habit.query.filter_by(user_id=current_user.id)
        .order_by(Habit.position.asc(), Habit.id.asc())
        .all()
    )

    # Get logs for the last 90 days for heat map
    ninety_days_ago = today - timedelta(days=90)
    logs = (
        HabitLog.query.filter(
            HabitLog.user_id == current_user.id,
            HabitLog.logged_date >= ninety_days_ago,
        )
        .order_by(HabitLog.logged_date.asc())
        .all()
    )

    # Build heat map data - activity per day
    activity_by_date = defaultdict(int)
    for log in logs:
        if log.delta > 0:  # Only count positive increments
            activity_by_date[log.logged_date] += log.delta

    # Get max activity for color scaling
    max_activity = max(activity_by_date.values()) if activity_by_date else 1

    # Build 13 weeks (91 days) of heat map data
    heatmap_weeks = []
    start_date = today - timedelta(days=90)
    # Adjust to start on Sunday
    start_date = start_date - timedelta(days=start_date.weekday() + 1)
    if start_date.weekday() != 6:  # 6 = Sunday
        start_date = start_date - timedelta(days=(start_date.weekday() + 1) % 7)

    current_date = start_date
    while current_date <= today:
        week = []
        for _ in range(7):
            if current_date <= today:
                activity = activity_by_date.get(current_date, 0)
                # Calculate intensity level (0-4)
                if activity == 0:
                    level = 0
                elif activity <= max_activity * 0.25:
                    level = 1
                elif activity <= max_activity * 0.5:
                    level = 2
                elif activity <= max_activity * 0.75:
                    level = 3
                else:
                    level = 4
                week.append(
                    {
                        "date": current_date,
                        "activity": activity,
                        "level": level,
                        "is_today": current_date == today,
                    }
                )
            else:
                week.append(None)
            current_date += timedelta(days=1)
        heatmap_weeks.append(week)

    # Weekly trend data (last 12 weeks)
    weekly_data = []
    for i in range(11, -1, -1):
        week_end = today - timedelta(days=today.weekday()) - timedelta(weeks=i)
        week_start = week_end - timedelta(days=6)
        week_total = sum(
            log.delta
            for log in logs
            if week_start <= log.logged_date <= week_end and log.delta > 0
        )
        weekly_data.append({"week": week_start.strftime("%b %d"), "total": week_total})

    # Monthly trend data (last 6 months)
    monthly_data = []
    for i in range(5, -1, -1):
        month_date = today.replace(day=1) - timedelta(days=i * 30)
        month_start = month_date.replace(day=1)
        if month_date.month == 12:
            month_end = month_date.replace(
                year=month_date.year + 1, month=1, day=1
            ) - timedelta(days=1)
        else:
            month_end = month_date.replace(
                month=month_date.month + 1, day=1
            ) - timedelta(days=1)

        month_total = sum(
            log.delta
            for log in logs
            if month_start <= log.logged_date <= month_end and log.delta > 0
        )
        monthly_data.append({"month": month_start.strftime("%b"), "total": month_total})

    # Day of week correlation (which days have most activity)
    day_of_week_totals = defaultdict(int)
    day_names = [
        "Monday",
        "Tuesday",
        "Wednesday",
        "Thursday",
        "Friday",
        "Saturday",
        "Sunday",
    ]
    for log in logs:
        if log.delta > 0:
            day_of_week_totals[log.logged_date.weekday()] += log.delta

    day_correlations = [
        {"day": day_names[i], "total": day_of_week_totals.get(i, 0)} for i in range(7)
    ]
    best_day_idx = max(range(7), key=lambda i: day_of_week_totals.get(i, 0))
    best_day = day_names[best_day_idx] if day_of_week_totals else None

    # Per-habit statistics
    habit_stats = []
    for habit in habits:
        habit_logs = [log for log in logs if log.habit_id == habit.id]
        total_increments = sum(log.delta for log in habit_logs if log.delta > 0)
        total_decrements = abs(sum(log.delta for log in habit_logs if log.delta < 0))

        # Days with activity in last 7 days
        week_ago = today - timedelta(days=7)
        week_activity_days = len(
            set(
                log.logged_date
                for log in habit_logs
                if log.logged_date >= week_ago and log.delta > 0
            )
        )

        # Per-habit day correlation
        habit_day_totals = defaultdict(int)
        for log in habit_logs:
            if log.delta > 0:
                habit_day_totals[log.logged_date.weekday()] += log.delta
        habit_best_day = None
        if habit_day_totals:
            habit_best_day_idx = max(
                habit_day_totals.keys(), key=lambda k: habit_day_totals[k]
            )
            habit_best_day = day_names[habit_best_day_idx]

        habit_stats.append(
            {
                "habit": habit,
                "total_increments": total_increments,
                "total_decrements": total_decrements,
                "week_activity_days": week_activity_days,
                "best_day": habit_best_day,
            }
        )

    # Best streaks (top 5 habits by best_streak)
    best_streaks = sorted(
        [h for h in habits if (h.best_streak or 0) > 0],
        key=lambda h: h.best_streak or 0,
        reverse=True,
    )[:5]

    # Weekly stats
    week_ago = today - timedelta(days=7)
    week_increments = sum(
        log.delta for log in logs if log.logged_date >= week_ago and log.delta > 0
    )
    week_active_habits = len(
        set(
            log.habit_id
            for log in logs
            if log.logged_date >= week_ago and log.delta > 0
        )
    )

    # Monthly stats
    month_ago = today - timedelta(days=30)
    month_increments = sum(
        log.delta for log in logs if log.logged_date >= month_ago and log.delta > 0
    )
    month_active_habits = len(
        set(
            log.habit_id
            for log in logs
            if log.logged_date >= month_ago and log.delta > 0
        )
    )

    return render_template(
        "habits/insights.html",
        habits=habits,
        heatmap_weeks=heatmap_weeks,
        weekly_data=weekly_data,
        monthly_data=monthly_data,
        day_correlations=day_correlations,
        best_day=best_day,
        habit_stats=habit_stats,
        best_streaks=best_streaks,
        week_increments=week_increments,
        week_active_habits=week_active_habits,
        month_increments=month_increments,
        month_active_habits=month_active_habits,
        total_habits=len(habits),
        today=today,
        max_activity=max_activity,
    )
