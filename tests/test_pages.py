def _login(client, email, password):
    response = client.post("/auth/login", data={"email": email, "password": password})
    assert response.status_code == 302


def test_admin_pages_render(client):
    _login(client, "admin@group18.local", "admin123")
    for url in ["/", "/orders", "/inventory", "/shipments", "/reports/orders"]:
        response = client.get(url, follow_redirects=True)
        assert response.status_code == 200, (url, response.status_code)


def test_customer_pages_render(client):
    _login(client, "customer@group18.local", "customer123")
    for url in ["/", "/orders", "/orders/new", "/shipments"]:
        response = client.get(url, follow_redirects=True)
        assert response.status_code == 200, (url, response.status_code)


def test_driver_pages_render(client):
    _login(client, "driver@group18.local", "driver123")
    for url in ["/", "/orders", "/shipments"]:
        response = client.get(url, follow_redirects=True)
        assert response.status_code == 200, (url, response.status_code)


def test_login_and_register_pages_render(client):
    assert client.get("/auth/login").status_code == 200
    assert client.get("/auth/register").status_code == 200
