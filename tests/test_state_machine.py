import pytest

from business.order_service import (
    DomainError,
    cancel_order,
    create_order,
    transition_order,
)
from data.models import InventoryItem, User


@pytest.fixture()
def ctx(app):
    db = app.config["DB"].session()
    customer = db.query(User).filter_by(email="customer@group18.local").one()
    driver = db.query(User).filter_by(email="driver@group18.local").one()
    admin = db.query(User).filter_by(email="admin@group18.local").one()
    item = db.query(InventoryItem).filter_by(stock_keeping_unit="SKU-001").one()
    yield {"db": db, "customer": customer, "driver": driver, "admin": admin, "item": item}
    app.config["DB"].remove()


def _new_order(ctx, quantity=2):
    return create_order(
        ctx["db"], ctx["customer"], [{"inventory_id": ctx["item"].id, "quantity": quantity}]
    )


def test_lifecycle_pending_to_closed(ctx):
    order = _new_order(ctx)
    assert order.status == "Pending"
    assert order.shipment is None

    transition_order(ctx["db"], order, ctx["admin"], "Ready", driver_id=ctx["driver"].id)
    assert order.status == "Ready"
    assert order.shipment is not None
    assert order.shipment.driver_id == ctx["driver"].id
    assert order.shipment.status == "Assigned"
    assert any(e.event_type == "Order Confirmed" for e in order.shipment.events)

    transition_order(ctx["db"], order, ctx["admin"], "InTransit")
    assert order.status == "InTransit"
    assert order.shipment.dispatched_at is not None

    transition_order(ctx["db"], order, ctx["driver"], "OutForDelivery", location="Kowloon Depot")
    transition_order(ctx["db"], order, ctx["driver"], "Delivered", location="Sha Tin")
    assert order.shipment.delivered_at is not None

    transition_order(ctx["db"], order, ctx["admin"], "Closed")
    assert order.status == "Closed"
    assert order.shipment.status == "Closed"


def test_illegal_forward_jump_rejected(ctx):
    order = _new_order(ctx)
    with pytest.raises(DomainError):
        transition_order(ctx["db"], order, ctx["admin"], "Delivered")


def test_wrong_role_cannot_confirm(ctx):
    order = _new_order(ctx)
    with pytest.raises(DomainError):
        transition_order(ctx["db"], order, ctx["customer"], "Ready")


def test_driver_cannot_advance_before_dispatch(ctx):
    order = _new_order(ctx)
    transition_order(ctx["db"], order, ctx["admin"], "Ready", driver_id=ctx["driver"].id)
    # order is Ready, not InTransit; a driver jump to OutForDelivery must fail
    with pytest.raises(DomainError):
        transition_order(ctx["db"], order, ctx["driver"], "OutForDelivery")


def test_cancel_pending_returns_stock(ctx):
    before = ctx["item"].quantity_on_hand
    order = _new_order(ctx, quantity=3)
    assert ctx["item"].quantity_on_hand == before - 3
    cancel_order(ctx["db"], order, ctx["customer"])
    assert order.status == "Cancelled"
    assert ctx["item"].quantity_on_hand == before


def test_cancel_ready_returns_stock_and_cancels_shipment(ctx):
    before = ctx["item"].quantity_on_hand
    order = _new_order(ctx, quantity=1)
    transition_order(ctx["db"], order, ctx["admin"], "Ready", driver_id=ctx["driver"].id)
    cancel_order(ctx["db"], order, ctx["customer"])
    assert order.status == "Cancelled"
    assert order.shipment.status == "Cancelled"
    assert ctx["item"].quantity_on_hand == before


def test_cancel_after_dispatch_rejected(ctx):
    order = _new_order(ctx)
    transition_order(ctx["db"], order, ctx["admin"], "Ready", driver_id=ctx["driver"].id)
    transition_order(ctx["db"], order, ctx["admin"], "InTransit")
    with pytest.raises(DomainError):
        cancel_order(ctx["db"], order, ctx["customer"])


def test_customer_cannot_cancel_someone_elses_order(ctx):
    order = _new_order(ctx)
    other = ctx["db"].query(User).filter_by(email="admin@group18.local").one()
    # admin is a different user; customer cancelling admin's order must fail
    other_order = create_order(
        ctx["db"],
        ctx["customer"],
        [{"inventory_id": ctx["item"].id, "quantity": 1}],
    )
    other_order.customer_id = other.id
    ctx["db"].commit()
    with pytest.raises(DomainError):
        cancel_order(ctx["db"], other_order, ctx["customer"])
