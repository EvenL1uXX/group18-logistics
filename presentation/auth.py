from flask import Blueprint, flash, g, redirect, render_template, request, session, url_for

from business.auth_service import AuthError, authenticate, register

auth_bp = Blueprint("auth", __name__, url_prefix="/auth")


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if session.get("user_id"):
        return redirect(url_for("index"))
    if request.method == "POST":
        user = authenticate(g.db, request.form.get("email", ""), request.form.get("password", ""))
        if user is None:
            flash("Invalid email or password.", "error")
        else:
            session.clear()
            session["user_id"] = user.id
            session["role"] = user.role_name
            return redirect(url_for("index"))
    return render_template("auth/login.html")


@auth_bp.route("/register", methods=["GET", "POST"])
def register_view():
    if session.get("user_id"):
        return redirect(url_for("index"))
    if request.method == "POST":
        try:
            user = register(
                g.db,
                request.form.get("email", ""),
                request.form.get("password", ""),
                request.form.get("full_name", ""),
                request.form.get("phone", ""),
            )
        except AuthError as exc:
            g.db.rollback()
            flash(str(exc), "error")
        else:
            session.clear()
            session["user_id"] = user.id
            session["role"] = user.role_name
            flash("Welcome! Your customer account is ready.", "success")
            return redirect(url_for("index"))
    return render_template("auth/register.html")


@auth_bp.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("auth.login"))
