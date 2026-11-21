import pytest

from business.inventory_service import InventoryError, stock_in, stock_out
from business.order_service import DomainError, cancel_order, create_order
from data.models import InventoryItem, User


@pytest.fixture()
def ctx(app):
    db = app.config["DB"].session()
    admin = db.query(User).filter_by(email="admin@group18.local").one()
    customer = db.query(User).filter_by(email="customer@group18.local").one()
    item = db.query(InventoryItem).filter_by(stock_keeping_unit="SKU-001").one()
    yield {"db": db, "admin": admin, "customer": customer, "item": item}
    app.config["DB"].remove()


def test_stock_in_increases_quantity(ctx):
    before = ctx["item"].quantity_on_hand
    stock_in(ctx["db"], ctx["item"].id, 25, ctx["admin"])
    assert ctx["item"].quantity_on_hand == before + 25


def test_stock_out_decreases_quantity(ctx):
    before = ctx["item"].quantity_on_hand
    stock_out(ctx["db"], ctx["item"].id, 5, ctx["admin"])
    assert ctx["item"].quantity_on_hand == before - 5


def test_stock_out_insufficient_rejected(ctx):
    with pytest.raises(InventoryError):
        stock_out(ctx["db"], ctx["item"].id, ctx["item"].quantity_on_hand + 1, ctx["admin"])


def test_order_reserves_stock_and_cancel_restores(ctx):
    before = ctx["item"].quantity_on_hand
    order = create_order(
        ctx["db"], ctx["customer"], [{"inventory_id": ctx["item"].id, "quantity": 4}]
    )
    assert ctx["item"].quantity_on_hand == before - 4
    cancel_order(ctx["db"], order, ctx["customer"])
    assert ctx["item"].quantity_on_hand == before


def test_order_above_stock_rejected(ctx):
    with pytest.raises(DomainError):
        create_order(
            ctx["db"],
            ctx["customer"],
            [{"inventory_id": ctx["item"].id, "quantity": ctx["item"].quantity_on_hand + 1}],
        )
