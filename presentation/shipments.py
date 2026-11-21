from flask import Blueprint, flash, g, redirect, render_template, request, url_for

from business.order_service import DomainError
from business.shipment_service import advance, get_shipment, list_for_user
from presentation import current_user, login_required

shipments_bp = Blueprint("shipments", __name__)


@shipments_bp.route("/shipments")
@login_required
def list_shipments():
    user = current_user(g.db)
    return render_template(
        "shipments/list.html", shipments=list_for_user(g.db, user), user=user
    )


@shipments_bp.route("/shipments/<int:shipment_id>")
@login_required
def detail(shipment_id: int):
    user = current_user(g.db)
    try:
        shipment = get_shipment(g.db, shipment_id, user)
    except DomainError as exc:
        flash(str(exc), "error")
        return redirect(url_for("shipments.list_shipments"))
    return render_template("shipments/detail.html", shipment=shipment, user=user)


@shipments_bp.route("/shipments/<int:shipment_id>/status", methods=["POST"])
@login_required
def update_status(shipment_id: int):
    user = current_user(g.db)
    try:
        shipment = get_shipment(g.db, shipment_id, user)
        target = request.form.get("target", "")
        location = request.form.get("location", "")
        advance(g.db, shipment, user, target, location)
    except DomainError as exc:
        g.db.rollback()
        flash(str(exc), "error")
    else:
        flash(f"Shipment updated: {target}.", "success")
    return redirect(url_for("shipments.detail", shipment_id=shipment_id))
