from app.services import payroll_service


def test_current_period_format():
    period = payroll_service.current_period()
    assert len(period) == 7
    assert period[4] == "-"


def test_get_or_create_payment_creates_row(app, db, seller_user):
    payment = payroll_service.get_or_create_payment(seller_user)
    assert payment.id is not None
    assert payment.is_paid is False
    assert payment.amount == seller_user.salary


def test_payment_history_covers_full_tenure(app, db, seller_user):
    history = payroll_service.payment_history(seller_user)
    # seller_user was hired 2026-01-01 in the fixture
    assert len(history) >= 1
    periods = [p.period for p in history]
    assert "2026-01" in periods


def test_mark_paid_and_unpaid(app, db, seller_user):
    payment = payroll_service.get_or_create_payment(seller_user)
    payroll_service.mark_paid(payment)
    assert payment.is_paid is True
    assert payment.paid_at is not None

    payroll_service.mark_unpaid(payment)
    assert payment.is_paid is False
    assert payment.paid_at is None


def test_toggle_payment_route(client, admin_user, seller_user):
    from tests.test_auth import login
    login(client, "testadmin", "password123")
    period = payroll_service.current_period()
    response = client.post(
        f"/admin/employees/{seller_user.id}/payments/{period}/toggle",
        follow_redirects=True,
    )
    assert response.status_code == 200
    assert b"Marked" in response.data


def test_employee_profile_shows_hr_details(client, admin_user, seller_user):
    from tests.test_auth import login
    login(client, "testadmin", "password123")
    response = client.get(f"/admin/employees/{seller_user.id}/profile")
    assert response.status_code == 200
    assert seller_user.full_name.encode() in response.data
    assert seller_user.phone.encode() in response.data
    assert seller_user.position.encode() in response.data
