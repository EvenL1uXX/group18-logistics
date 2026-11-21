"""Database models for the Group 18 Logistics Management System.

Eight tables follow the ER diagram in the project handbook:
roles, users, orders, order_items, inventory, shipments,
tracking_events, audit_log.
"""

from datetime import datetime
from decimal import Decimal

from sqlalchemy import DateTime, ForeignKey, Integer, Numeric, String
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


# ---- Order status machine -------------------------------------------------
ORDER_STATUSES = [
    "Pending",
    "Ready",
    "InTransit",
    "OutForDelivery",
    "Delivered",
    "Closed",
]
CANCELLED_STATUS = "Cancelled"
CANCELLABLE_STATUSES = {"Pending", "Ready"}

# legal forward transitions: current status -> allowed next status
LEGAL_ORDER_TRANSITIONS = {
    "Pending": {"Ready"},
    "Ready": {"InTransit"},
    "InTransit": {"OutForDelivery"},
    "OutForDelivery": {"Delivered"},
    "Delivered": {"Closed"},
    "Closed": set(),
    "Cancelled": set(),
}


class Role(Base):
    __tablename__ = "roles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(32), unique=True, nullable=False)

    users: Mapped[list["User"]] = relationship(back_populates="role")


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    email: Mapped[str] = mapped_column(String(120), unique=True, index=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str] = mapped_column(String(80), nullable=False)
    phone: Mapped[str | None] = mapped_column(String(30), nullable=True)
    role_id: Mapped[int] = mapped_column(ForeignKey("roles.id"), nullable=False)

    role: Mapped[Role] = relationship(back_populates="users")
    orders: Mapped[list["Order"]] = relationship(back_populates="customer")
    driven_shipments: Mapped[list["Shipment"]] = relationship(back_populates="driver")

    @property
    def role_name(self) -> str:
        return self.role.name if self.role else ""


class Order(Base):
    __tablename__ = "orders"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    customer_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="Pending", index=True, nullable=False)
    total_amount: Mapped[Decimal] = mapped_column(Numeric(10, 2), default=Decimal("0.00"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.now, onupdate=datetime.now, nullable=False
    )

    customer: Mapped[User] = relationship(back_populates="orders")
    items: Mapped[list["OrderItem"]] = relationship(
        back_populates="order", cascade="all, delete-orphan"
    )
    shipment: Mapped["Shipment | None"] = relationship(back_populates="order", uselist=False)

    @property
    def tracking_number(self) -> str:
        return f"ORD-{self.id:05d}"


class OrderItem(Base):
    __tablename__ = "order_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    order_id: Mapped[int] = mapped_column(ForeignKey("orders.id"), nullable=False)
    inventory_id: Mapped[int] = mapped_column(ForeignKey("inventory.id"), nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    unit_price: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    subtotal: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)

    order: Mapped[Order] = relationship(back_populates="items")
    inventory_item: Mapped["InventoryItem"] = relationship(back_populates="order_items")


class InventoryItem(Base):
    __tablename__ = "inventory"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    stock_keeping_unit: Mapped[str] = mapped_column(String(40), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    quantity_on_hand: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    unit_price: Mapped[Decimal] = mapped_column(Numeric(10, 2), default=Decimal("0.00"), nullable=False)
    location: Mapped[str] = mapped_column(String(80), default="", nullable=False)

    order_items: Mapped[list[OrderItem]] = relationship(back_populates="inventory_item")


class Shipment(Base):
    __tablename__ = "shipments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    order_id: Mapped[int] = mapped_column(ForeignKey("orders.id"), unique=True, nullable=False)
    driver_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="Assigned", nullable=False)
    dispatched_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    delivered_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    order: Mapped[Order] = relationship(back_populates="shipment")
    driver: Mapped[User | None] = relationship(back_populates="driven_shipments")
    events: Mapped[list["TrackingEvent"]] = relationship(
        back_populates="shipment", cascade="all, delete-orphan", order_by="TrackingEvent.event_time"
    )

    @property
    def tracking_number(self) -> str:
        return f"SHP-{self.id:05d}"


class TrackingEvent(Base):
    __tablename__ = "tracking_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    shipment_id: Mapped[int] = mapped_column(ForeignKey("shipments.id"), nullable=False)
    event_type: Mapped[str] = mapped_column(String(40), nullable=False)
    location: Mapped[str] = mapped_column(String(80), default="", nullable=False)
    event_time: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, nullable=False)
    recorded_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)

    shipment: Mapped[Shipment] = relationship(back_populates="events")
    recorder: Mapped[User | None] = relationship()


class AuditLog(Base):
    __tablename__ = "audit_log"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    action: Mapped[str] = mapped_column(String(40), nullable=False)
    entity: Mapped[str] = mapped_column(String(40), nullable=False)
    entity_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, nullable=False)

    user: Mapped[User | None] = relationship()
