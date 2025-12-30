"""
Search Blueprint - global search across user data
"""
from flask import Blueprint, render_template, request, url_for
from flask_login import current_user, login_required
from sqlalchemy import or_

from models import (
    Daily,
    Goal,
    Habit,
    Idea,
    MasterCategory,
    MasterSection,
    ShoppingList,
    Todo,
)

search_bp = Blueprint("search", __name__, url_prefix="/search")


def _like(field, q):
    return field.ilike(f"%{q}%")


def _make_result(kind, title, url, snippet=None):
    return {"kind": kind, "title": title, "url": url, "snippet": snippet or ""}


@search_bp.route("/", methods=["GET"])
@login_required
def search():
    q = (request.args.get("q") or "").strip()
    results = {
        "Todos": [],
        "Dailies": [],
        "Habits": [],
        "Goals": [],
        "Shopping": [],
        "Masterprompts": [],
        "Ideas": [],
    }

    if q:
        uid = current_user.id
        # Todos
        todos = (
            Todo.query.filter(Todo.user_id == uid)
            .filter(or_(_like(Todo.title, q), _like(Todo.description, q)))
            .order_by(Todo.created_at.desc())
            .limit(20)
            .all()
        )
        for t in todos:
            results["Todos"].append(
                _make_result(
                    "Todo",
                    t.title,
                    url_for("todos.edit_todo", todo_id=t.id),
                    (t.description or "")[:160],
                )
            )

        # Dailies
        dailies = (
            Daily.query.filter(Daily.user_id == uid)
            .filter(or_(_like(Daily.title, q), _like(Daily.description, q)))
            .order_by(Daily.created_at.desc())
            .limit(20)
            .all()
        )
        for d in dailies:
            results["Dailies"].append(
                _make_result(
                    "Daily",
                    d.title,
                    url_for("dailies.edit_daily", daily_id=d.id),
                    (d.description or "")[:160],
                )
            )

        # Habits
        habits = (
            Habit.query.filter(Habit.user_id == uid)
            .filter(or_(_like(Habit.title, q), _like(Habit.description, q)))
            .order_by(Habit.created_at.desc())
            .limit(20)
            .all()
        )
        for h in habits:
            results["Habits"].append(
                _make_result(
                    "Habit",
                    h.title,
                    url_for("habits.edit_habit", habit_id=h.id),
                    (h.description or "")[:160],
                )
            )

        # Goals
        goals = (
            Goal.query.filter(Goal.user_id == uid)
            .filter(or_(_like(Goal.title, q), _like(Goal.description, q)))
            .order_by(Goal.created_at.desc())
            .limit(20)
            .all()
        )
        for g in goals:
            results["Goals"].append(
                _make_result(
                    "Goal",
                    g.title,
                    url_for("goals.edit", id=g.id),
                    (g.description or "")[:160],
                )
            )

        # Shopping lists
        lists = (
            ShoppingList.query.filter(ShoppingList.user_id == uid)
            .filter(or_(_like(ShoppingList.title, q), _like(ShoppingList.items, q)))
            .order_by(ShoppingList.updated_at.desc())
            .limit(20)
            .all()
        )
        for s in lists:
            results["Shopping"].append(
                _make_result(
                    "Shopping",
                    s.title,
                    url_for("shopping.edit", id=s.id),
                    (s.items or "")[:160],
                )
            )

        # Masterprompts categories and sections
        cats = (
            MasterCategory.query.filter(MasterCategory.user_id == uid)
            .filter(_like(MasterCategory.name, q))
            .order_by(MasterCategory.position, MasterCategory.id)
            .limit(20)
            .all()
        )
        for c in cats:
            results["Masterprompts"].append(
                _make_result(
                    "Category", c.name, url_for("masterprompts.index", category_id=c.id)
                )
            )

        secs = (
            MasterSection.query.filter(MasterSection.user_id == uid)
            .filter(or_(_like(MasterSection.title, q), _like(MasterSection.body, q)))
            .order_by(MasterSection.created_at.desc())
            .limit(20)
            .all()
        )
        for s in secs:
            results["Masterprompts"].append(
                _make_result(
                    "Section",
                    s.title,
                    url_for("masterprompts.index", category_id=s.category_id),
                    s.body[:160],
                )
            )

        # Ideas
        ideas = (
            Idea.query.filter(Idea.user_id == uid)
            .filter(
                or_(
                    _like(Idea.title, q),
                    _like(Idea.description, q),
                    _like(Idea.notes, q),
                )
            )
            .order_by(Idea.updated_at.desc())
            .limit(20)
            .all()
        )
        for i in ideas:
            results["Ideas"].append(
                _make_result(
                    "Idea",
                    i.title,
                    url_for("ideas.view_idea", idea_id=i.id),
                    (i.description or i.notes or "")[:160],
                )
            )

    return render_template("search/results.html", q=q, results=results)
