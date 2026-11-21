"""Idempotent seed data: roles, one account per role, a few inventory items."""

from werkzeug.security import generate_password_hash

from data.models import InventoryItem, Role, User

DEMO_USERS = [
    # email, password, full name, role, phone
    ("admin@group18.local", "admin123", "Cheng Admin", "Admin", "9000 1111"),
    ("driver@group18.local", "driver123", "Wong Driver", "Driver", "9000 2222"),
    ("customer@group18.local", "customer123", "Li Customer", "Customer", "9000 3333"),
]

DEMO_STOCK = [
    # sku, name, on hand, unit price, location
    ("SKU-001", "Standard Carton Box", 120, "18.50", "A-01"),
    ("SKU-002", "Wooden Pallet", 40, "95.00", "B-02"),
    ("SKU-003", "Packing Tape Roll", 300, "6.80", "A-03"),
    ("SKU-004", "Bubble Wrap Roll", 80, "32.00", "B-01"),
    ("SKU-005", "Return Label Pack", 150, "12.00", "C-01"),
]


def seed(db) -> None:
    roles = {}
    for name in ("Customer", "Driver", "Admin"):
        role = db.query(Role).filter_by(name=name).first()
        if role is None:
            role = Role(name=name)
            db.add(role)
            db.flush()
        roles[name] = role

    for email, password, full_name, role_name, phone in DEMO_USERS:
        if db.query(User).filter_by(email=email).first() is None:
            db.add(
                User(
                    email=email,
                    password_hash=generate_password_hash(password),
                    full_name=full_name,
                    phone=phone,
                    role=roles[role_name],
                )
            )

    for sku, name, quantity, price, location in DEMO_STOCK:
        if db.query(InventoryItem).filter_by(stock_keeping_unit=sku).first() is None:
            db.add(
                InventoryItem(
                    stock_keeping_unit=sku,
                    name=name,
                    quantity_on_hand=quantity,
                    unit_price=price,
                    location=location,
                )
            )

    db.commit()


def seed_database(db) -> None:
    seed(db)
