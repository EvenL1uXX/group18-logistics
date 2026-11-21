"""Presentation layer: Flask blueprints, templates and static assets."""

from functools import wraps

from flask import g, redirect, session, url_for

from data.models import User


def current_user(db) -> User | None:
    user_id = session.get("user_id")
    if user_id is None:
        return None
    return db.get(User, user_id)


def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not session.get("user_id"):
            return redirect(url_for("auth.login"))
        return view(*args, **kwargs)

    return wrapped
