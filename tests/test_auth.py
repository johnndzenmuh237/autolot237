def login(client, username, password):
    return client.post("/login", data={"username": username, "password": password}, follow_redirects=True)


def test_login_success(client, admin_user):
    response = login(client, "testadmin", "password123")
    assert response.status_code == 200
    assert b"Dashboard" in response.data


def test_login_failure(client, admin_user):
    response = login(client, "testadmin", "wrongpassword")
    assert response.status_code == 200
    assert b"Invalid username or password" in response.data


def test_seller_cannot_access_admin_pages(client, seller_user):
    login(client, "testseller", "password123")
    response = client.get("/admin/dashboard")
    assert response.status_code == 403


def test_admin_can_register_seller(client, admin_user):
    login(client, "testadmin", "password123")
    response = client.post(
        "/employees/register",
        data={
            "full_name": "New Seller", "username": "newseller", "password": "pw12345",
            "phone": "+237 600 000 000", "address": "Douala, Bonanjo",
            "position": "Shop Attendant", "salary": "80000", "hire_date": "2026-01-15",
        },
        follow_redirects=True,
    )
    assert response.status_code == 200
    assert b"New Seller" in response.data


def test_registration_requires_full_hr_details(client, admin_user, app, db):
    login(client, "testadmin", "password123")
    response = client.post(
        "/employees/register",
        data={"full_name": "Incomplete Seller", "username": "incomplete", "password": "pw12345"},
        follow_redirects=True,
    )
    assert response.status_code == 200
    assert b"Phone number and address are required" in response.data
    from app.models.user import User
    assert User.query.filter_by(username="incomplete").first() is None


def test_logout_requires_login_after(client, admin_user):
    login(client, "testadmin", "password123")
    client.get("/logout")
    response = client.get("/admin/dashboard", follow_redirects=True)
    assert b"Sign in" in response.data or b"Welcome back" not in response.data
