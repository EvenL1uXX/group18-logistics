import csv
import io

from sqlalchemy import func

from data.models import Order


def order_summary(db) -> dict:
    rows = db.query(Order.status, func.count(Order.id)).group_by(Order.status).all()
    by_status = {status: count for status, count in rows}
    total_orders = sum(by_status.values())
    revenue = (
        db.query(func.coalesce(func.sum(Order.total_amount), 0))
        .filter(Order.status.in_(["Delivered", "Closed"]))
        .scalar()
    )
    cancelled = by_status.get("Cancelled", 0)
    return {
        "total_orders": total_orders,
        "by_status": by_status,
        "revenue": float(revenue or 0),
        "cancelled": cancelled,
    }


def orders_as_csv(db) -> str:
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(
        ["order_id", "tracking_number", "customer", "status", "total_amount", "created_at"]
    )
    for order in db.query(Order).order_by(Order.id).all():
        writer.writerow(
            [
                order.id,
                order.tracking_number,
                order.customer.full_name if order.customer else "",
                order.status,
                f"{float(order.total_amount):.2f}",
                order.created_at.strftime("%Y-%m-%d %H:%M"),
            ]
        )
    return buffer.getvalue()
