from flask import Blueprint, flash, g, redirect, render_template, request, url_for

from business.order_service import (
    DomainError,
    cancel_order,
    create_order,
    get_order,
    transition_order,
    visible_orders,
)
from data.models import Role, User
from presentation import current_user, login_required

orders_bp = Blueprint("orders", __name__)


def _drivers(db):
    return db.query(User).join(Role).filter(Role.name == "Driver").order_by(User.full_name).all()


@orders_bp.route("/orders")
@login_required
def list_orders():
    user = current_user(g.db)
    return render_template(
        "orders/list.html", orders=visible_orders(g.db, user), user=user
    )


@orders_bp.route("/orders/new", methods=["GET", "POST"])
@login_required
def new_order():
    user = current_user(g.db)
    from business.inventory_service import list_items

    items = list_items(g.db)
    if request.method == "POST":
        raw_items = []
        index = 1
        while True:
            inventory_id = request.form.get(f"inventory_id_{index}")
            if inventory_id is None:
                break
            quantity = request.form.get(f"quantity_{index}", "")
            if inventory_id and quantity:
                raw_items.append({"inventory_id": inventory_id, "quantity": quantity})
            index += 1
        try:
            order = create_order(g.db, user, raw_items)
        except DomainError as exc:
            g.db.rollback()
            flash(str(exc), "error")
        else:
            flash(f"Order {order.tracking_number} placed. Status: Pending.", "success")
            return redirect(url_for("orders.detail", order_id=order.id))
    return render_template("orders/new.html", items=items, user=user)


@orders_bp.route("/orders/<int:order_id>")
@login_required
def detail(order_id: int):
    user = current_user(g.db)
    try:
        order = get_order(g.db, order_id, user)
    except DomainError as exc:
        flash(str(exc), "error")
        return redirect(url_for("orders.list_orders"))
    return render_template(
        "orders/detail.html", order=order, user=user, drivers=_drivers(g.db)
    )


@orders_bp.route("/orders/<int:order_id>/cancel", methods=["POST"])
@login_required
def cancel(order_id: int):
    user = current_user(g.db)
    try:
        order = get_order(g.db, order_id, user)
        cancel_order(g.db, order, user)
    except DomainError as exc:
        g.db.rollback()
        flash(str(exc), "error")
    else:
        flash(f"Order {order.tracking_number} cancelled; stock returned.", "success")
    return redirect(url_for("orders.detail", order_id=order_id))


@orders_bp.route("/orders/<int:order_id>/confirm", methods=["POST"])
@login_required
def confirm(order_id: int):
    user = current_user(g.db)
    try:
        order = get_order(g.db, order_id, user)
        driver_id = request.form.get("driver_id") or None
        transition_order(g.db, order, user, "Ready", driver_id=int(driver_id) if driver_id else None)
    except DomainError as exc:
        g.db.rollback()
        flash(str(exc), "error")
    else:
        flash(f"Order {order.tracking_number} confirmed. Shipment created.", "success")
    return redirect(url_for("orders.detail", order_id=order_id))


@orders_bp.route("/orders/<int:order_id>/dispatch", methods=["POST"])
@login_required
def dispatch(order_id: int):
    user = current_user(g.db)
    try:
        order = get_order(g.db, order_id, user)
        transition_order(g.db, order, user, "InTransit")
    except DomainError as exc:
        g.db.rollback()
        flash(str(exc), "error")
    else:
        flash(f"Order {order.tracking_number} dispatched: now In Transit.", "success")
    return redirect(url_for("orders.detail", order_id=order_id))


@orders_bp.route("/orders/<int:order_id>/close", methods=["POST"])
@login_required
def close(order_id: int):
    user = current_user(g.db)
    try:
        order = get_order(g.db, order_id, user)
        transition_order(g.db, order, user, "Closed")
    except DomainError as exc:
        g.db.rollback()
        flash(str(exc), "error")
    else:
        flash(f"Order {order.tracking_number} closed.", "success")
    return redirect(url_for("orders.detail", order_id=order_id))
