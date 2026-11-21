from flask import Blueprint, flash, g, redirect, render_template, request, url_for

from business.inventory_service import InventoryError, list_items, stock_in, stock_out
from presentation import current_user, login_required

inventory_bp = Blueprint("inventory", __name__)


@inventory_bp.route("/inventory")
@login_required
def list_inventory():
    user = current_user(g.db)
    if user.role_name != "Admin":
        flash("Only an administrator can view inventory.", "error")
        return redirect(url_for("index"))
    return render_template("inventory/list.html", items=list_items(g.db), user=user)


@inventory_bp.route("/inventory/stock-in", methods=["POST"])
@login_required
def receive_stock():
    user = current_user(g.db)
    try:
        item_id = int(request.form.get("item_id", "0"))
        quantity = int(request.form.get("quantity", "0"))
        stock_in(g.db, item_id, quantity, user)
    except (InventoryError, ValueError) as exc:
        g.db.rollback()
        flash(str(exc), "error")
    else:
        flash("Stock received.", "success")
    return redirect(url_for("inventory.list_inventory"))


@inventory_bp.route("/inventory/stock-out", methods=["POST"])
@login_required
def issue_stock():
    user = current_user(g.db)
    try:
        item_id = int(request.form.get("item_id", "0"))
        quantity = int(request.form.get("quantity", "0"))
        stock_out(g.db, item_id, quantity, user)
    except (InventoryError, ValueError) as exc:
        g.db.rollback()
        flash(str(exc), "error")
    else:
        flash("Stock issued.", "success")
    return redirect(url_for("inventory.list_inventory"))
