from flask import Blueprint, Response, flash, g, redirect, render_template, url_for

from business.report_service import order_summary, orders_as_csv
from presentation import current_user, login_required

reports_bp = Blueprint("reports", __name__)


@reports_bp.route("/reports/orders")
@login_required
def orders_report():
    user = current_user(g.db)
    if user.role_name != "Admin":
        flash("Only an administrator can view reports.", "error")
        return redirect(url_for("index"))
    return render_template(
        "reports/index.html", summary=order_summary(g.db), user=user
    )


@reports_bp.route("/reports/orders.csv")
@login_required
def orders_csv():
    user = current_user(g.db)
    if user.role_name != "Admin":
        flash("Only an administrator can export reports.", "error")
        return redirect(url_for("index"))
    return Response(
        orders_as_csv(g.db),
        mimetype="text/csv",
        headers={"Content-Disposition": "attachment; filename=group18_orders.csv"},
    )
