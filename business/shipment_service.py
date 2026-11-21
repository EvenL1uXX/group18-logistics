from data.models import Order, Shipment
from business.order_service import DomainError, transition_order


def list_for_user(db, user):
    if user.role_name == "Admin":
        return db.query(Shipment).order_by(Shipment.id.desc()).all()
    if user.role_name == "Customer":
        return (
            db.query(Shipment)
            .join(Shipment.order)
            .filter(Order.customer_id == user.id)
            .order_by(Shipment.id.desc())
            .all()
        )
    return (
        db.query(Shipment)
        .filter(Shipment.driver_id == user.id)
        .order_by(Shipment.id.desc())
        .all()
    )


def get_shipment(db, shipment_id: int, user) -> Shipment:
    shipment = db.get(Shipment, shipment_id)
    if shipment is None:
        raise DomainError("Shipment not found.")
    if user.role_name == "Admin":
        return shipment
    if user.role_name == "Driver" and shipment.driver_id == user.id:
        return shipment
    if user.role_name == "Customer" and shipment.order.customer_id == user.id:
        return shipment
    raise DomainError("You do not have access to this shipment.")


def advance(db, shipment: Shipment, actor, target: str, location: str = "") -> Shipment:
    """Driver updates progress; delegates to the order state machine."""
    transition_order(db, shipment.order, actor, target, location=location)
    db.refresh(shipment)
    return shipment
