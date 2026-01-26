"""
Stats Blueprint - fun statistics dashboard to motivate users
"""
from datetime import date, timedelta

from flask import Blueprint, jsonify, render_template, request
from flask_login import current_user, login_required

from extensions import db
from models import CompletionLog, Daily, DailyStats, EntityTag, Habit, Tag, Todo

stats_bp = Blueprint("stats", __name__, url_prefix="/stats")


@stats_bp.route("/")
@login_required
def dashboard():
    """Main stats dashboard with fun statistics"""
    # Get filter parameters
    filter_tag_id = request.args.get("tag", type=int)
    days_back = request.args.get("days", default=30, type=int)

    # Get all user tags for filter dropdown
    all_tags = Tag.query.filter_by(user_id=current_user.id).order_by(Tag.name).all()
    selected_tag = None
    if filter_tag_id:
        selected_tag = Tag.query.filter_by(
            id=filter_tag_id, user_id=current_user.id
        ).first()

    # Calculate stats
    perfect_days = DailyStats.get_perfect_days_count(current_user.id)
    current_streak = DailyStats.get_current_streak(current_user.id)
    best_streak = DailyStats.get_best_streak(current_user.id)
    avg_completion = DailyStats.get_average_completion(current_user.id, days_back)

    # Get recent stats for chart (last N days)
    cutoff_date = date.today() - timedelta(days=days_back)
    recent_stats = (
        DailyStats.query.filter(
            DailyStats.user_id == current_user.id, DailyStats.stat_date >= cutoff_date
        )
        .order_by(DailyStats.stat_date.asc())
        .all()
    )

    # Total completions from CompletionLog
    total_completions = CompletionLog.query.filter_by(user_id=current_user.id).count()

    # Daily streaks (from Daily model)
    dailies = Daily.query.filter_by(user_id=current_user.id).all()
    total_daily_streaks = sum(d.streak_count for d in dailies)
    best_daily_streak = max((d.best_streak for d in dailies), default=0)

    # Habit stats
    habits = Habit.query.filter_by(user_id=current_user.id).all()
    total_habit_count = sum(h.count for h in habits)

    # Filter by tag if specified
    tag_stats = None
    if filter_tag_id and selected_tag:
        # Get completion counts for items with this tag
        tag_stats = _get_tag_stats(current_user.id, filter_tag_id, days_back)

    # Fun motivational messages based on stats
    motivation = _get_motivation_message(perfect_days, current_streak, avg_completion)

    # Prepare chart data
    chart_labels = [s.stat_date.strftime("%b %d") for s in recent_stats]
    chart_data = [s.completion_percentage for s in recent_stats]

    return render_template(
        "stats/dashboard.html",
        perfect_days=perfect_days,
        current_streak=current_streak,
        best_streak=best_streak,
        avg_completion=avg_completion,
        total_completions=total_completions,
        total_daily_streaks=total_daily_streaks,
        best_daily_streak=best_daily_streak,
        total_habit_count=total_habit_count,
        recent_stats=recent_stats,
        chart_labels=chart_labels,
        chart_data=chart_data,
        all_tags=all_tags,
        selected_tag=selected_tag,
        tag_stats=tag_stats,
        days_back=days_back,
        motivation=motivation,
    )


@stats_bp.route("/api/data")
@login_required
def api_data():
    """API endpoint for chart data"""
    days_back = request.args.get("days", default=30, type=int)
    cutoff_date = date.today() - timedelta(days=days_back)

    stats = (
        DailyStats.query.filter(
            DailyStats.user_id == current_user.id, DailyStats.stat_date >= cutoff_date
        )
        .order_by(DailyStats.stat_date.asc())
        .all()
    )

    return jsonify(
        {
            "labels": [s.stat_date.isoformat() for s in stats],
            "data": [s.completion_percentage for s in stats],
            "todos": [s.todos_completed for s in stats],
            "dailies": [s.dailies_completed for s in stats],
            "habits": [s.habits_completed for s in stats],
        }
    )


def _get_tag_stats(user_id: int, tag_id: int, days_back: int) -> dict:
    """Get completion stats for items with a specific tag"""
    cutoff_date = date.today() - timedelta(days=days_back)

    # Get entity IDs with this tag
    tagged_todos = (
        db.session.query(EntityTag.entity_id)
        .filter(EntityTag.tag_id == tag_id, EntityTag.entity_type == "todo")
        .subquery()
    )

    tagged_dailies = (
        db.session.query(EntityTag.entity_id)
        .filter(EntityTag.tag_id == tag_id, EntityTag.entity_type == "daily")
        .subquery()
    )

    # Count completed todos with this tag
    todo_completions = Todo.query.filter(
        Todo.user_id == user_id, Todo.id.in_(tagged_todos), Todo.status == "completed"
    ).count()

    # Count total todos with this tag
    todo_total = Todo.query.filter(
        Todo.user_id == user_id, Todo.id.in_(tagged_todos)
    ).count()

    # Count dailies with this tag and their completions
    dailies_with_tag = Daily.query.filter(
        Daily.user_id == user_id, Daily.id.in_(tagged_dailies)
    ).all()

    daily_completions = sum(d.total_completions for d in dailies_with_tag)
    daily_total = len(dailies_with_tag)

    return {
        "todo_completions": todo_completions,
        "todo_total": todo_total,
        "daily_completions": daily_completions,
        "daily_total": daily_total,
    }


def _get_motivation_message(
    perfect_days: int, current_streak: int, avg_completion: float
) -> str:
    """Generate a fun motivational message based on stats"""
    messages = []

    if perfect_days == 0:
        messages.append("🎯 Your first perfect day is waiting!")
    elif perfect_days == 1:
        messages.append("🌟 You got your first perfect day! Keep it up!")
    elif perfect_days < 10:
        messages.append(f"⭐ {perfect_days} perfect days! You're building momentum!")
    elif perfect_days < 50:
        messages.append(f"🔥 {perfect_days} perfect days! You're on fire!")
    elif perfect_days < 100:
        messages.append(f"🏆 {perfect_days} perfect days! Almost to 100!")
    else:
        messages.append(f"👑 {perfect_days} perfect days! You're a legend!")

    if current_streak >= 7:
        messages.append(f"🔥 {current_streak}-day streak! Don't break the chain!")
    elif current_streak >= 3:
        messages.append(f"📈 {current_streak}-day streak going strong!")

    if avg_completion >= 90:
        messages.append("💯 Your average is amazing!")
    elif avg_completion >= 70:
        messages.append("💪 Great consistency!")

    return " ".join(messages) if messages else "Keep going! Every day counts!"


def save_daily_stats(user_id: int, stat_date: date, stats_data: dict) -> DailyStats:
    """Save or update daily stats for a user"""
    daily_stats = DailyStats.get_or_create(user_id, stat_date)

    daily_stats.todos_completed = stats_data.get("todos_completed", 0)
    daily_stats.todos_total = stats_data.get("todos_total", 0)
    daily_stats.dailies_completed = stats_data.get("dailies_completed", 0)
    daily_stats.dailies_total = stats_data.get("dailies_total", 0)
    daily_stats.habits_completed = stats_data.get("habits_completed", 0)
    daily_stats.habits_total = stats_data.get("habits_total", 0)

    daily_stats.total_completed = (
        daily_stats.todos_completed
        + daily_stats.dailies_completed
        + daily_stats.habits_completed
    )
    daily_stats.total_items = (
        daily_stats.todos_total + daily_stats.dailies_total + daily_stats.habits_total
    )

    if daily_stats.total_items > 0:
        daily_stats.completion_percentage = int(
            round((daily_stats.total_completed / daily_stats.total_items) * 100)
        )
    else:
        daily_stats.completion_percentage = 0

    db.session.commit()
    return daily_stats
