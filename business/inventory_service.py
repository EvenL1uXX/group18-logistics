from datetime import datetime

from data.models import AuditLog, InventoryItem


class InventoryError(ValueError):
    """Raised when a stock operation is invalid."""


def list_items(db):
    return db.query(InventoryItem).order_by(InventoryItem.stock_keeping_unit).all()


def _audit(db, actor, action: str, item: InventoryItem) -> None:
    db.add(
        AuditLog(
            user_id=actor.id if actor else None,
            action=action,
            entity="inventory",
            entity_id=item.id,
        )
    )


def stock_in(db, item_id: int, quantity: int, actor) -> InventoryItem:
    if actor.role_name != "Admin":
        raise InventoryError("Only an administrator can receive stock.")
    if not isinstance(quantity, int) or quantity <= 0:
        raise InventoryError("Quantity must be a positive integer.")
    item = db.get(InventoryItem, item_id)
    if item is None:
        raise InventoryError("Inventory item not found.")
    item.quantity_on_hand += quantity
    _audit(db, actor, "stock_in", item)
    db.commit()
    return item


def stock_out(db, item_id: int, quantity: int, actor) -> InventoryItem:
    if actor.role_name != "Admin":
        raise InventoryError("Only an administrator can issue stock.")
    if not isinstance(quantity, int) or quantity <= 0:
        raise InventoryError("Quantity must be a positive integer.")
    item = db.get(InventoryItem, item_id)
    if item is None:
        raise InventoryError("Inventory item not found.")
    if item.quantity_on_hand < quantity:
        raise InventoryError(
            f"Insufficient stock for {item.name}: only {item.quantity_on_hand} on hand."
        )
    item.quantity_on_hand -= quantity
    _audit(db, actor, "stock_out", item)
    db.commit()
    return item
