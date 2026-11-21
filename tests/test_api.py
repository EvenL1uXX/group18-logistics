from data.models import Shipment, User


def _login(client, email, password):
    response = client.post(
        "/auth/login", data={"email": email, "password": password}
    )
    assert response.status_code == 302, response.data[:500]
    return response


def test_orders_require_login(client):
    response = client.get("/orders")
    assert response.status_code == 302
    assert "/auth/login" in response.headers["Location"]


def test_full_happy_path_over_http(app, client):
    _login(client, "customer@group18.local", "customer123")
    response = client.post(
        "/orders/new", data={"inventory_id_1": "1", "quantity_1": "1"}
    )
    assert response.status_code == 302
    location = response.headers["Location"]
    order_id = int(location.rstrip("/").split("/")[-1])

    client.get("/auth/logout")
    _login(client, "admin@group18.local", "admin123")

    db = app.config["DB"].session()
    driver_id = db.query(User).filter_by(email="driver@group18.local").one().id
    app.config["DB"].remove()

    response = client.post(f"/orders/{order_id}/confirm", data={"driver_id": str(driver_id)})
    assert response.status_code == 302
    response = client.post(f"/orders/{order_id}/dispatch")
    assert response.status_code == 302

    client.get("/auth/logout")
    _login(client, "driver@group18.local", "driver123")

    db = app.config["DB"].session()
    shipment_id = db.query(Shipment).filter_by(order_id=order_id).one().id
    app.config["DB"].remove()

    response = client.post(
        f"/shipments/{shipment_id}/status",
        data={"target": "OutForDelivery", "location": "Kowloon Depot"},
    )
    assert response.status_code == 302
    response = client.post(
        f"/shipments/{shipment_id}/status",
        data={"target": "Delivered", "location": "Sha Tin"},
    )
    assert response.status_code == 302

    client.get("/auth/logout")
    _login(client, "admin@group18.local", "admin123")
    response = client.post(f"/orders/{order_id}/close")
    assert response.status_code == 302

    page = client.get(f"/orders/{order_id}")
    assert page.status_code == 200
    assert b"Closed" in page.data


def test_customer_cannot_read_admin_inventory(app, client):
    _login(client, "customer@group18.local", "customer123")
    response = client.get("/inventory")
    assert response.status_code == 302
