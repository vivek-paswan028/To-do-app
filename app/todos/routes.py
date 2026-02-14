from __future__ import annotations

from datetime import date, timedelta

from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required
from sqlalchemy import or_

from ..extensions import db
from ..models import Category, Todo


todos_bp = Blueprint("todos", __name__)

VALID_STATUSES = {"todo", "in_progress", "done"}
VALID_PRIORITIES = {"low", "medium", "high"}


def _parse_due_date(raw_value: str) -> date | None:
    if not raw_value:
        return None
    try:
        return date.fromisoformat(raw_value)
    except ValueError:
        return None


def _clean_status(value: str) -> str:
    return value if value in VALID_STATUSES else "todo"


def _clean_priority(value: str) -> str:
    return value if value in VALID_PRIORITIES else "medium"


def _user_todo_or_404(task_id: int) -> Todo:
    return Todo.query.filter_by(id=task_id, user_id=current_user.id).first_or_404()


def _user_category_or_none(category_id: str) -> Category | None:
    if not category_id.isdigit():
        return None
    return Category.query.filter_by(id=int(category_id), user_id=current_user.id).first()


@todos_bp.get("/")
@login_required
def index():
    query = request.args.get("q", "").strip()
    status = request.args.get("status", "all")
    priority = request.args.get("priority", "all")
    category_id = request.args.get("category", "all")
    due = request.args.get("due", "all")

    todos_query = Todo.query.filter_by(user_id=current_user.id)

    if query:
        pattern = f"%{query}%"
        todos_query = todos_query.filter(
            or_(Todo.title.ilike(pattern), Todo.description.ilike(pattern))
        )

    if status in VALID_STATUSES:
        todos_query = todos_query.filter(Todo.status == status)

    if priority in VALID_PRIORITIES:
        todos_query = todos_query.filter(Todo.priority == priority)

    if category_id != "all" and category_id.isdigit():
        todos_query = todos_query.filter(Todo.category_id == int(category_id))

    if due == "today":
        todos_query = todos_query.filter(Todo.due_date == date.today())
    elif due == "week":
        todos_query = todos_query.filter(
            Todo.due_date >= date.today(), Todo.due_date <= (date.today() + timedelta(days=7))
        )
    elif due == "overdue":
        todos_query = todos_query.filter(Todo.due_date < date.today(), Todo.status != "done")

    todos = todos_query.order_by(Todo.is_pinned.desc(), Todo.updated_at.desc()).all()

    base_todos = Todo.query.filter_by(user_id=current_user.id)
    stats = {
        "all": base_todos.count(),
        "todo": base_todos.filter_by(status="todo").count(),
        "in_progress": base_todos.filter_by(status="in_progress").count(),
        "done": base_todos.filter_by(status="done").count(),
        "overdue": base_todos.filter(Todo.due_date < date.today(), Todo.status != "done").count(),
    }

    categories = Category.query.filter_by(user_id=current_user.id).order_by(Category.name.asc()).all()

    filters = {
        "q": query,
        "status": status,
        "priority": priority,
        "category": category_id,
        "due": due,
    }

    return render_template(
        "todos/index.html",
        todos=todos,
        categories=categories,
        stats=stats,
        filters=filters,
        valid_statuses=sorted(VALID_STATUSES),
        valid_priorities=sorted(VALID_PRIORITIES),
    )


@todos_bp.post("/tasks")
@login_required
def create_task():
    title = request.form.get("title", "").strip()
    description = request.form.get("description", "").strip()
    status = _clean_status(request.form.get("status", "todo"))
    priority = _clean_priority(request.form.get("priority", "medium"))
    due_date = _parse_due_date(request.form.get("due_date", "").strip())
    category = request.form.get("category_id", "").strip()

    if not title:
        flash("Task title is required.", "error")
        return redirect(url_for("todos.index"))

    category_obj = _user_category_or_none(category)

    todo = Todo(
        title=title,
        description=description,
        status=status,
        priority=priority,
        due_date=due_date,
        category_id=category_obj.id if category_obj else None,
        user_id=current_user.id,
    )
    db.session.add(todo)
    db.session.commit()
    flash("Task created.", "success")
    return redirect(url_for("todos.index"))


@todos_bp.post("/tasks/<int:task_id>/status")
@login_required
def update_status(task_id: int):
    task = _user_todo_or_404(task_id)
    status = _clean_status(request.form.get("status", "todo"))
    task.status = status
    db.session.commit()
    flash("Task status updated.", "success")
    return redirect(url_for("todos.index", **request.args))


@todos_bp.post("/tasks/<int:task_id>/pin")
@login_required
def toggle_pin(task_id: int):
    task = _user_todo_or_404(task_id)
    task.is_pinned = not task.is_pinned
    db.session.commit()
    flash("Task pin updated.", "success")
    return redirect(url_for("todos.index", **request.args))


@todos_bp.get("/tasks/<int:task_id>/edit")
@login_required
def edit_task_form(task_id: int):
    task = _user_todo_or_404(task_id)
    categories = Category.query.filter_by(user_id=current_user.id).order_by(Category.name.asc()).all()
    return render_template(
        "todos/edit.html",
        task=task,
        categories=categories,
        valid_statuses=sorted(VALID_STATUSES),
        valid_priorities=sorted(VALID_PRIORITIES),
    )


@todos_bp.post("/tasks/<int:task_id>/edit")
@login_required
def edit_task(task_id: int):
    task = _user_todo_or_404(task_id)

    title = request.form.get("title", "").strip()
    if not title:
        flash("Task title is required.", "error")
        return redirect(url_for("todos.edit_task_form", task_id=task.id))

    task.title = title
    task.description = request.form.get("description", "").strip()
    task.status = _clean_status(request.form.get("status", "todo"))
    task.priority = _clean_priority(request.form.get("priority", "medium"))
    task.due_date = _parse_due_date(request.form.get("due_date", "").strip())

    category = request.form.get("category_id", "").strip()
    category_obj = _user_category_or_none(category)
    task.category_id = category_obj.id if category_obj else None

    db.session.commit()
    flash("Task updated.", "success")
    return redirect(url_for("todos.index"))


@todos_bp.post("/tasks/<int:task_id>/delete")
@login_required
def delete_task(task_id: int):
    task = _user_todo_or_404(task_id)
    db.session.delete(task)
    db.session.commit()
    flash("Task deleted.", "success")
    return redirect(url_for("todos.index"))


@todos_bp.post("/categories")
@login_required
def create_category():
    name = request.form.get("name", "").strip()
    if not name:
        flash("Category name is required.", "error")
        return redirect(url_for("todos.index"))

    exists = Category.query.filter(
        Category.user_id == current_user.id, Category.name.ilike(name)
    ).first()
    if exists:
        flash("Category already exists.", "error")
        return redirect(url_for("todos.index"))

    db.session.add(Category(name=name, user_id=current_user.id))
    db.session.commit()
    flash("Category created.", "success")
    return redirect(url_for("todos.index"))


@todos_bp.post("/tasks/clear-completed")
@login_required
def clear_completed():
    deleted = Todo.query.filter_by(status="done", user_id=current_user.id).delete()
    db.session.commit()
    flash(f"Cleared {deleted} completed task(s).", "success")
    return redirect(url_for("todos.index"))
