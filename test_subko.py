import pytest
from fastapi.testclient import TestClient
import sqlite3
import os
import uuid

from main import app
from database import get_connection, init_db

client = TestClient(app)

def setup_module():
    init_db()

def test_menu_endpoint():
    response = client.get("/api/menu")
    assert response.status_code == 200
    items = response.json()
    assert len(items) >= 10
    # Verify categories and prices
    assert any(i["category"] == "Specialty Coffee" for i in items)
    assert any(i["category"] == "Craft Bakehouse" for i in items)
    assert any(i["name"] == "Riverdale Estate Pour-Over" for i in items)

def test_user_registration_and_login():
    unique_email = f"patron_{uuid.uuid4().hex[:6]}@example.com"
    # Register
    reg_res = client.post("/api/auth/register", json={
        "full_name": "Aarav Sharma",
        "email": unique_email,
        "phone": "+919876543210",
        "password": "SecurePassword123"
    })
    assert reg_res.status_code == 200
    data = reg_res.json()
    assert data["success"] is True
    assert data["user"]["email"] == unique_email
    assert "token" in data

    # Duplicate registration should fail
    dup_res = client.post("/api/auth/register", json={
        "full_name": "Aarav Sharma",
        "email": unique_email,
        "phone": "+919876543210",
        "password": "SecurePassword123"
    })
    assert dup_res.status_code == 400

    # Login
    login_res = client.post("/api/auth/login", json={
        "email": unique_email,
        "password": "SecurePassword123"
    })
    assert login_res.status_code == 200
    assert login_res.json()["success"] is True
    assert "token" in login_res.json()

def test_table_booking_flow():
    payload = {
        "customer_name": "Pooja Varma",
        "customer_email": "pooja.varma@example.com",
        "customer_phone": "+919123456789",
        "reservation_date": "2026-11-05",
        "reservation_time": "11:00 AM",
        "guests_count": 3,
        "service_type": "Cupping Room Experience",
        "special_notes": "Window table if possible"
    }
    res = client.post("/api/bookings", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert data["success"] is True
    assert data["booking_ref"].startswith("SBK-BK-")

    # Verify directly in SQLite database
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM bookings WHERE booking_ref = ?", (data["booking_ref"],))
    row = cursor.fetchone()
    conn.close()
    assert row is not None
    assert row["customer_name"] == "Pooja Varma"
    assert row["status"] == "Confirmed"

def test_order_creation_and_price_snapshot():
    # Fetch menu items to get valid IDs and prices
    menu_res = client.get("/api/menu")
    items = menu_res.json()
    item1 = items[0]
    item2 = items[1]

    order_payload = {
        "customer_name": "Rohan Deshmukh",
        "customer_email": "rohan.d@example.com",
        "customer_phone": "+919811223344",
        "delivery_type": "Dine-in Pick-up",
        "delivery_address": "Mary Lodge Counter",
        "items": [
            {"item_id": item1["id"], "quantity": 2},
            {"item_id": item2["id"], "quantity": 1}
        ]
    }
    
    expected_subtotal = (item1["price"] * 2) + (item2["price"] * 1)
    expected_tax = round(expected_subtotal * 0.05, 2)
    expected_total = round(expected_subtotal + expected_tax, 2)

    res = client.post("/api/orders", json=order_payload)
    assert res.status_code == 200
    data = res.json()
    assert data["success"] is True
    assert data["order_ref"].startswith("SBK-ORD-")
    assert abs(data["subtotal"] - expected_subtotal) < 0.01
    assert abs(data["tax"] - expected_tax) < 0.01
    assert abs(data["total"] - expected_total) < 0.01

    # Verify immutable price snapshot in database
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM order_items WHERE order_id = ?", (data["order_id"],))
    line_items = cursor.fetchall()
    conn.close()
    
    assert len(line_items) == 2
    for li in line_items:
        if li["item_id"] == item1["id"]:
            assert li["unit_price_snapshot"] == item1["price"]
            assert li["quantity"] == 2
            assert li["line_total"] == item1["price"] * 2
        elif li["item_id"] == item2["id"]:
            assert li["unit_price_snapshot"] == item2["price"]
            assert li["quantity"] == 1
            assert li["line_total"] == item2["price"] * 1

def test_staff_admin_operations():
    # Login as seeded admin
    login_res = client.post("/api/auth/login", json={
        "email": "staff@subko.coffee",
        "password": "SubkoStaff@2026"
    })
    assert login_res.status_code == 200
    token = login_res.json()["token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Test staff stats
    stats_res = client.get("/api/stats", headers=headers)
    assert stats_res.status_code == 200
    stats = stats_res.json()
    assert "total_revenue" in stats
    assert "total_orders" in stats
    assert "active_bookings" in stats

    # Test listing all orders
    orders_res = client.get("/api/orders", headers=headers)
    assert orders_res.status_code == 200
    orders = orders_res.json()
    assert len(orders) >= 1
    first_order_id = orders[0]["id"]

    # Test updating status
    patch_res = client.patch(f"/api/orders/{first_order_id}/status", json={"status": "Preparing"}, headers=headers)
    assert patch_res.status_code == 200
    assert patch_res.json()["status"] == "Preparing"

if __name__ == "__main__":
    pytest.main(["-v", __file__])
