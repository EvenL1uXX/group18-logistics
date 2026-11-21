**GitHub repository:** `<https://github.com/EvanLiu_xx/group18-logistics>` — replace with the live URL before submission.

# COMP 3500SEF — Group 18 Logistics Management System

## 1. Introduction

Small logistics operators still coordinate orders, warehouse stock and deliveries on paper or in separate spreadsheets. Group 18 builds a compact web application that covers the four modules agreed during the progress review: users and roles, orders, warehouse inventory and shipment tracking. The system is deliberately small — no payment, no real map, no mobile app — so that the whole order lifecycle can be demonstrated end to end. The progress review presented the requirements and design; this report documents the implementation, testing and evolution that followed.

## 2. Stakeholders and Requirements

Three actors drive the requirements. Customers place orders and watch their status; drivers receive assigned shipments and report progress; administrators confirm and dispatch orders, maintain stock and view reports. The requirements package contains 20 user stories, 13 of them Must, and five measurable non-functional requirements: order lists of 1,000 records within two seconds, salted passwords and strict role isolation, core operations in under three steps, transactional order submission, and a README that lets a new member run the project within one day. Out of scope: payments, real maps, multi-warehouse transfer, a mobile app and push notifications.

## 3. Design

The design follows the artefacts from the review. The context diagram bounds the system with three actors and four modules. Five use cases — Place Order, Check Status, Stock In, Stock Out and Transport and Delivery — cover the lifecycle. The class model has eight classes, with Customer, Driver and Admin inheriting from User. The ER model has eight tables: roles, users, orders, order_items, inventory, shipments, tracking_events and audit_log. Orders move through a seven-state machine (Pending, Ready, In Transit, Out for Delivery, Delivered, Closed) with a Cancelled branch available before dispatch. The architecture is a three-layer monolith — presentation, business and data — rendered on the server, with SQLite as the single data store. Three architecture decisions were recorded with trade-offs: monolith over microservices, server-side rendering over a separate SPA, and SQLite over MySQL.

## 4. Implementation

The stack is Flask 3, SQLAlchemy 2, SQLite, Jinja2 and Bootstrap 5. Code is split along the architecture: `presentation/` holds the blueprints, templates and static assets; `business/` holds five services (auth, order, inventory, shipment, report); `data/` holds the eight SQLAlchemy models, the session factory and the demo seed. Dependencies point one way, from presentation to business to data, so the state machine and stock rules can be tested without a browser.

The order state machine is enforced in one place, `order_service.transition_order`. It checks the requested transition against a legal-transition table, checks the actor's role (only an admin confirms, dispatches and closes; only the assigned driver advances delivery), applies the side effects — creating the shipment at confirmation, stamping dispatch and delivery times, appending a tracking event — and writes an audit row.

Stock is reserved when an order is placed: the service prices the lines, checks and deducts `quantity_on_hand` in the same transaction, and lists the order at Pending. Cancellation is allowed only in Pending or Ready and returns the reserved quantity; dispatch does not deduct again. A shipment is created 1:1 with an order at confirmation and its status follows the order, staying Assigned until dispatch. Every state change appends a tracking event with timestamp, optional location and actor, and the audit_log records who changed what.

Authentication uses session cookies and salted Werkzeug password hashes. Role checks live in the service layer rather than only in the navigation, so a customer who types an admin URL is still refused. Tracking numbers are display identifiers derived from primary keys (ORD-00001, SHP-00001).

## 5. Testing

Testing follows the three layers in the test plan: unit, API and acceptance. The suite has 20 pytest tests against a fresh SQLite database per test. Unit tests cover every legal transition of the order state machine, every illegal jump and the role guards; cancellation is tested at all three boundaries — pending, ready and after dispatch. Inventory tests cover stock in, stock out, insufficient stock, and the reserve-on-order / restore-on-cancel rule. The API test drives the full happy path over HTTP: customer signs in and places an order, admin confirms with a driver and dispatches, driver marks the shipment out for delivery and delivered, admin closes the order. A role-based access test confirms a customer cannot open the inventory page. Page smoke tests load every screen for all three roles. The demo accounts and a one-command seed let a marker reproduce the same flow.

## 6. Evolution

Changes follow the change-request table in the handbook: a request records what changes, why, which artefacts are affected and who decided. The system supports the usual maintenance types — corrective fixes to the state machine, adaptive changes to configuration, and perfective work such as the CSV report. The most likely evolution is a repository layer between services and models, CSRF protection, pagination, and optional multi-warehouse support behind a feature gate; none of these change the external behaviour of the current order lifecycle.

## 7. Process and Collaboration

The seven-person team coordinated through a WeChat group and a shared task board with three states. Design artefacts were frozen after the progress review; the implementation phase [[CONFIRM: two-person scope — Product Owner plus AI pair-programming]] delivered the code in this repository, while the team's design and review material remains the source of truth for the requirements. [[CONFIRM: AI usage declaration wording]].

## 8. Conclusion

The project delivers a working MVP: customer ordering, administrator confirmation, dispatch, driver delivery updates, order closure, cancellation with stock release, inventory management and a summary report, all backed by 20 automated tests. The repository is ready for the demonstration video and for the maintenance work described above.
