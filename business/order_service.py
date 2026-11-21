from datetime import datetime
from decimal import Decimal

from data.models import (
    AuditLog,
    CANCELLABLE_STATUSES,
    CANCELLED_STATUS,
    InventoryItem,
    LEGAL_ORDER_TRANSITIONS,
    Order,
    OrderItem,
    Shipment,
    TrackingEvent,
)


class DomainError(ValueError):
    """Business rule violation; the UI shows this message to the user."""


def _audit(db, actor, action: str, entity: str, entity_id: int) -> None:
    db.add(
        AuditLog(
            user_id=actor.id if actor is not None else None,
            action=action,
            entity=entity,
            entity_id=entity_id,
        )
    )


def _event(db, shipment: Shipment, event_type: str, actor, location: str = "") -> None:
    db.add(
        TrackingEvent(
            shipment=shipment,
            event_type=event_type,
            location=location,
            event_time=datetime.now(),
            recorded_by=actor.id if actor is not None else None,
        )
    )


def _price_items(db, raw_items):
    """Validate requested quantities and return (inventory_item, qty, subtotal) rows.

    Stock is checked but not modified here.
    """
    if not raw_items:
        raise DomainError("The order must contain at least one item.")
    priced = []
    for raw in raw_items:
        try:
            inventory_id = int(raw["inventory_id"])
            quantity = int(raw["quantity"])
        except (KeyError, TypeError, ValueError):
            raise DomainError("Each order line needs a valid item and quantity.")
        if quantity <= 0:
            raise DomainError("Quantity must be a positive number.")
        item = db.get(InventoryItem, inventory_id)
        if item is None:
            raise DomainError("One of the selected inventory items does not exist.")
        if item.quantity_on_hand < quantity:
            raise DomainError(
                f"Insufficient stock for {item.name}: only {item.quantity_on_hand} left."
            )
        priced.append((item, quantity))
    return priced


def create_order(db, customer, raw_items) -> Order:
    """Place an order: reserve stock, price the lines, create the order."""
    if customer.role_name != "Customer":
        raise DomainError("Only a customer can place an order.")
    priced = _price_items(db, raw_items)
    for item, qty in priced:
        item.quantity_on_hand -= qty

    order = Order(customer_id=customer.id, status="Pending")
    total = Decimal("0.00")
    for item, qty in priced:
        subtotal = item.unit_price * qty
        total += subtotal
        order.items.append(
            OrderItem(
                inventory_id=item.id,
                quantity=qty,
                unit_price=item.unit_price,
                subtotal=subtotal,
            )
        )
    order.total_amount = total
    db.add(order)
    db.flush()
    _audit(db, customer, "order_created", "order", order.id)
    db.commit()
    return order


def cancel_order(db, order: Order, actor) -> Order:
    """Cancel a not-yet-dispatched order and return its reserved stock."""
    if order.status not in CANCELLABLE_STATUSES:
        raise DomainError(
            "This order can no longer be cancelled: it has already been dispatched."
        )
    if actor.role_name == "Customer" and order.customer_id != actor.id:
        raise DomainError("You can only cancel your own orders.")
    if actor.role_name not in ("Customer", "Admin"):
        raise DomainError("Only the customer or an administrator can cancel an order.")

    for line in order.items:
        item = db.get(InventoryItem, line.inventory_id)
        if item is not None:
            item.quantity_on_hand += line.quantity
    order.status = CANCELLED_STATUS
    order.updated_at = datetime.now()
    if order.shipment is not None:
        order.shipment.status = CANCELLED_STATUS
    _audit(db, actor, "order_cancelled", "order", order.id)
    db.commit()
    return order


def _ensure_transition_actor(order: Order, actor, target: str) -> None:
    if actor is None:
        raise DomainError("You must be signed in.")
    role = actor.role_name
    if target in ("Ready", "InTransit", "Closed") and role != "Admin":
        raise DomainError("Only an administrator can perform this step.")
    if target in ("OutForDelivery", "Delivered"):
        if role != "Driver":
            raise DomainError("Only the assigned driver can perform this step.")
        if order.shipment is None or order.shipment.driver_id != actor.id:
            raise DomainError("This shipment is not assigned to you.")


def _apply_transition(db, order: Order, actor, current: str, target: str, driver_id, location: str) -> None:
    now = datetime.now()
    if target == "Ready":
        if order.shipment is not None:
            raise DomainError("This order already has a shipment.")
        shipment = Shipment(
            order=order,
            driver_id=driver_id,
            status="Assigned",
            dispatched_at=None,
            delivered_at=None,
        )
        db.add(shipment)
        db.flush()
        _event(db, shipment, "Order Confirmed", actor)
    elif target == "InTransit":
        if order.shipment is None:
            raise DomainError("Confirm the order and assign a driver first.")
        order.shipment.dispatched_at = now
        _event(db, order.shipment, "Dispatched", actor, location)
    elif target == "OutForDelivery":
        _event(db, order.shipment, "Out for Delivery", actor, location)
    elif target == "Delivered":
        order.shipment.delivered_at = now
        _event(db, order.shipment, "Delivered", actor, location)
    elif target == "Closed":
        pass


def transition_order(db, order: Order, actor, target: str, driver_id=None, location: str = "") -> Order:
    """Move an order along the state machine, enforcing role and transition rules."""
    current = order.status
    if target not in LEGAL_ORDER_TRANSITIONS.get(current, set()):
        raise DomainError(f"Cannot move an order from {current} to {target}.")
    _ensure_transition_actor(order, actor, target)
    _apply_transition(db, order, actor, current, target, driver_id, location)

    order.status = target
    order.updated_at = datetime.now()
    if order.shipment is not None:
        # a shipment created at "Ready" stays Assigned until dispatch
        order.shipment.status = "Assigned" if target == "Ready" else target
    _audit(db, actor, f"order_{target.lower()}", "order", order.id)
    db.commit()
    return order


def visible_orders(db, user):
    """Orders a user may see: admin all, customer own, driver the ones they ship."""
    from data.models import User

    if user.role_name == "Admin":
        return db.query(Order).order_by(Order.created_at.desc()).all()
    if user.role_name == "Customer":
        return (
            db.query(Order)
            .filter(Order.customer_id == user.id)
            .order_by(Order.created_at.desc())
            .all()
        )
    driver_orders = (
        db.query(Order)
        .join(Shipment, Shipment.order_id == Order.id)
        .filter(Shipment.driver_id == user.id)
        .order_by(Order.created_at.desc())
        .all()
    )
    return driver_orders


def get_order(db, order_id: int, user) -> Order:
    order = db.get(Order, order_id)
    if order is None:
        raise DomainError("Order not found.")
    if user.role_name == "Admin":
        return order
    if user.role_name == "Customer" and order.customer_id == user.id:
        return order
    if (
        user.role_name == "Driver"
        and order.shipment is not None
        and order.shipment.driver_id == user.id
    ):
        return order
    raise DomainError("You do not have access to this order.")
