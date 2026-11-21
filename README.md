# Group 18 — Logistics Management System

COMP 3500SEF Group 18 project. A small, server-rendered web application for
order intake, warehouse stock, shipment tracking and order reports.

Built with Flask 3 + SQLAlchemy 2 + SQLite + Jinja2 + Bootstrap 5 (vendored
locally, no CDN needed at runtime).

## Quick start

```bash
pip install -r requirements.txt
python seed_db.py          # creates instance/logistics.db and demo data
python app.py              # http://127.0.0.1:5000
```

Demo accounts:

| Role     | Email                    | Password     |
|----------|--------------------------|--------------|
| Customer | `customer@group18.local` | `customer123` |
| Driver   | `driver@group18.local`   | `driver123`   |
| Admin    | `admin@group18.local`    | `admin123`    |

Customers can also register their own account from `/auth/register`.

## Main flow

`Place order → Admin confirms (assigns driver) → Admin dispatches →
Driver starts delivery → Driver confirms delivery → Admin closes`

Stock is reserved when the order is placed and released if the customer
cancels before dispatch. A shipment is created at confirmation and moves
1:1 with its order.

## Order state machine

```
Pending → Ready → InTransit → OutForDelivery → Delivered → Closed
   │        │
   └────────┴──────────────→ Cancelled        (customer, before dispatch)
```

Illegal jumps (for example `Pending → Delivered`) and cancellation after
dispatch are rejected by the service layer with a readable message.

## Roles

- **Customer** — register/login, place orders, see own orders and shipment
  timeline, cancel own order while `Pending` or `Ready`.
- **Driver** — login, see only shipments assigned to them, advance
  `InTransit → OutForDelivery → Delivered` with an optional location note.
- **Admin** — confirm/dispatch/close orders, assign drivers, view and adjust
  stock, view order summary and export CSV.

## Routes

| Method | Path | Role | Purpose |
|--------|------|------|---------|
| GET/POST | `/auth/login` | all | Sign in |
| GET/POST | `/auth/register` | all | Customer self-registration |
| GET | `/auth/logout` | all | Sign out |
| GET | `/orders` | all (filtered) | Order list |
| GET/POST | `/orders/new` | Customer | Place order |
| GET | `/orders/<id>` | owner/admin/driver | Order detail + timeline |
| POST | `/orders/<id>/cancel` | Customer/Admin | Cancel before dispatch |
| POST | `/orders/<id>/confirm` | Admin | Pending → Ready, create shipment |
| POST | `/orders/<id>/dispatch` | Admin | Ready → InTransit |
| POST | `/orders/<id>/close` | Admin | Delivered → Closed |
| GET | `/inventory` | Admin | Stock list |
| POST | `/inventory/stock-in` | Admin | Receive stock |
| POST | `/inventory/stock-out` | Admin | Issue stock (with stock check) |
| GET | `/shipments` | all (filtered) | Shipment list |
| GET | `/shipments/<id>` | owner/admin/driver | Shipment + tracking timeline |
| POST | `/shipments/<id>/status` | Driver | Advance delivery status |
| GET | `/reports/orders` | Admin | Order summary |
| GET | `/reports/orders.csv` | Admin | CSV export |

The route design follows the 10-endpoint API list in the project handbook;
confirmation and dispatch were split into explicit order endpoints so each
state change stays traceable.

## Architecture

```
app.py            Flask app factory, session per request
data/             models (8 tables), session factory, demo seed
business/         auth, order, inventory, shipment, report services
presentation/     blueprints, Jinja templates, static assets
tests/            state machine, inventory, HTTP flows, page smoke tests
```

Dependencies point one way: presentation → business → data.

Eight tables: `roles`, `users`, `orders`, `order_items`, `inventory`,
`shipments`, `tracking_events`, `audit_log`.

## Design decisions

- **Monolith + server-side rendering + SQLite** — one small team, one
  deployable unit, zero database operations.
- **Stock reserved at order time.** The order service checks and deducts
  `quantity_on_hand` inside one transaction; cancellation returns it.
  Dispatch does not deduct again. This is what makes “cancel releases stock”
  true and “insufficient stock is blocked” testable.
- **Shipment is 1:1 with an order**, created when the admin confirms and
  assigns a driver. Its `status` follows the order, staying `Assigned`
  between confirmation and dispatch.
- **Tracking numbers** are display identifiers derived from primary keys:
  `ORD-00001` for orders and `SHP-00001` for shipments.
- **Session-cookie authentication**, salted password hashes via Werkzeug.
- **Role checks live in the service layer**, not only in the navbar.

## Tests

```bash
python -m pytest -q
```

Covers:

- full state-machine lifecycle and every illegal jump;
- cancellation boundary (`Pending`/`Ready` only) with stock released;
- stock in/out and insufficient-stock rejection;
- order placement reserving stock and cancelling restoring it;
- HTTP happy path (customer → admin → driver → admin);
- role-based access (customer cannot open the inventory page);
- page smoke tests for all three roles.

## Known limitations

- No CSRF tokens (course-project scope; the app is for local demo).
- No pagination for order/shipment lists.
- Reports are a simple summary + CSV export.
- One warehouse; multi-warehouse transfer is explicitly out of scope.
