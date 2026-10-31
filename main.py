from fastapi import FastAPI, Request, Response, HTTPException, Depends, status
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from pydantic import BaseModel, EmailStr
from typing import Optional, List
import uuid
import datetime
import os
import sqlite3

from database import get_connection, hash_password, verify_password, init_db
from auth import create_access_token, decode_access_token

app = FastAPI(title="Subko Coffee Roasters & Craft Bakehouse", version="1.0.0")

BASE_DIR = os.path.dirname(__file__)
STATIC_DIR = os.path.join(BASE_DIR, "static")
TEMPLATES_DIR = os.path.join(BASE_DIR, "templates")

os.makedirs(STATIC_DIR, exist_ok=True)
os.makedirs(TEMPLATES_DIR, exist_ok=True)

app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
templates = Jinja2Templates(directory=TEMPLATES_DIR)

# Ensure database is initialized
init_db()

# Models
class RegisterRequest(BaseModel):
    full_name: str
    email: EmailStr
    phone: str
    password: str

class LoginRequest(BaseModel):
    email: EmailStr
    password: str

class BookingCreateRequest(BaseModel):
    customer_name: str
    customer_email: EmailStr
    customer_phone: str
    reservation_date: str # YYYY-MM-DD
    reservation_time: str # HH:MM
    guests_count: int
    service_type: str # 'Table Reservation', 'Cupping Room Experience', 'Private Brew Session'
    special_notes: Optional[str] = ""

class CartItem(BaseModel):
    item_id: int
    quantity: int

class OrderCreateRequest(BaseModel):
    customer_name: str
    customer_email: EmailStr
    customer_phone: str
    delivery_type: str # 'Dine-in Pick-up', 'Takeaway', 'Local Delivery'
    delivery_address: Optional[str] = ""
    items: List[CartItem]

class StatusUpdateRequest(BaseModel):
    status: str

# Helper to get current user from token or cookie
def get_current_user(request: Request) -> Optional[dict]:
    token = request.cookies.get("subko_session")
    if not token:
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header.split(" ")[1]
    
    if not token:
        return None
        
    payload = decode_access_token(token)
    if not payload:
        return None
        
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, full_name, email, phone, role FROM users WHERE id = ?", (payload.get("user_id"),))
    user = cursor.fetchone()
    conn.close()
    
    if user:
        return dict(user)
    return None

# API: Auth
@app.post("/api/auth/register")
def register(req: RegisterRequest, response: Response):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM users WHERE email = ?", (req.email.lower(),))
    if cursor.fetchone():
        conn.close()
        raise HTTPException(status_code=400, detail="An account with this email already exists.")
    
    hashed = hash_password(req.password)
    cursor.execute("""
        INSERT INTO users (full_name, email, phone, password_hash, role)
        VALUES (?, ?, ?, ?, 'customer')
    """, (req.full_name.strip(), req.email.lower().strip(), req.phone.strip(), hashed))
    user_id = cursor.lastrowid
    conn.commit()
    conn.close()
    
    token = create_access_token({"user_id": user_id, "role": "customer", "name": req.full_name})
    response.set_cookie(key="subko_session", value=token, httponly=True, max_age=86400*7)
    return {
        "success": True,
        "token": token,
        "user": {
            "id": user_id,
            "full_name": req.full_name,
            "email": req.email.lower(),
            "phone": req.phone,
            "role": "customer"
        }
    }

@app.post("/api/auth/login")
def login(req: LoginRequest, response: Response):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE email = ?", (req.email.lower().strip(),))
    user = cursor.fetchone()
    conn.close()
    
    if not user or not verify_password(user["password_hash"], req.password):
        raise HTTPException(status_code=401, detail="Invalid email address or password.")
    
    token = create_access_token({"user_id": user["id"], "role": user["role"], "name": user["full_name"]})
    response.set_cookie(key="subko_session", value=token, httponly=True, max_age=86400*7)
    return {
        "success": True,
        "token": token,
        "user": {
            "id": user["id"],
            "full_name": user["full_name"],
            "email": user["email"],
            "phone": user["phone"],
            "role": user["role"]
        }
    }

@app.post("/api/auth/logout")
def logout(response: Response):
    response.delete_cookie(key="subko_session")
    return {"success": True, "message": "Logged out successfully"}

@app.get("/api/auth/me")
def me(user: Optional[dict] = Depends(get_current_user)):
    if not user:
        return {"authenticated": False}
    return {"authenticated": True, "user": user}

# API: Menu
@app.get("/api/menu")
def get_menu():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM menu_items WHERE is_available = 1 ORDER BY category, id")
    items = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return items

# API: Bookings (Table & Cupping Experience)
@app.post("/api/bookings")
def create_booking(req: BookingCreateRequest, user: Optional[dict] = Depends(get_current_user)):
    ref = f"SBK-BK-{uuid.uuid4().hex[:6].upper()}"
    user_id = user["id"] if user else None
    
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO bookings (
            booking_ref, user_id, customer_name, customer_email, 
            customer_phone, reservation_date, reservation_time, 
            guests_count, service_type, special_notes, status
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'Confirmed')
    """, (
        ref, user_id, req.customer_name, req.customer_email.lower(),
        req.customer_phone, req.reservation_date, req.reservation_time,
        req.guests_count, req.service_type, req.special_notes
    ))
    booking_id = cursor.lastrowid
    conn.commit()
    conn.close()
    
    return {
        "success": True,
        "booking_id": booking_id,
        "booking_ref": ref,
        "message": f"Table reserved successfully under reference {ref}."
    }

@app.get("/api/bookings")
def list_bookings(user: Optional[dict] = Depends(get_current_user)):
    conn = get_connection()
    cursor = conn.cursor()
    
    if user and user["role"] == "admin":
        cursor.execute("SELECT * FROM bookings ORDER BY created_at DESC")
    elif user:
        cursor.execute("SELECT * FROM bookings WHERE user_id = ? OR customer_email = ? ORDER BY created_at DESC", 
                       (user["id"], user["email"]))
    else:
        conn.close()
        return []
        
    bookings = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return bookings

@app.patch("/api/bookings/{booking_id}/status")
def update_booking_status(booking_id: int, req: StatusUpdateRequest, user: Optional[dict] = Depends(get_current_user)):
    if not user or user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Staff access required.")
    
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE bookings SET status = ? WHERE id = ?", (req.status, booking_id))
    conn.commit()
    conn.close()
    return {"success": True, "status": req.status}

# API: Orders & Strict Price Snapshotting
@app.post("/api/orders")
def create_order(req: OrderCreateRequest, user: Optional[dict] = Depends(get_current_user)):
    if not req.items:
        raise HTTPException(status_code=400, detail="Cart is empty.")
    
    conn = get_connection()
    cursor = conn.cursor()
    
    # 1. Fetch live prices to verify and calculate immutable snapshot
    subtotal = 0.0
    line_items_data = []
    
    for item in req.items:
        cursor.execute("SELECT id, name, price, is_available FROM menu_items WHERE id = ?", (item.item_id,))
        row = cursor.fetchone()
        if not row or not row["is_available"]:
            conn.close()
            raise HTTPException(status_code=400, detail=f"Item ID {item.item_id} is currently unavailable.")
        
        unit_price = float(row["price"])
        qty = int(item.quantity)
        line_total = unit_price * qty
        subtotal += line_total
        
        line_items_data.append({
            "item_id": row["id"],
            "item_name": row["name"],
            "unit_price_snapshot": unit_price,
            "quantity": qty,
            "line_total": line_total
        })
        
    # GST in India for dining/food delivery: 5%
    tax_amount = round(subtotal * 0.05, 2)
    total_amount = round(subtotal + tax_amount, 2)
    order_ref = f"SBK-ORD-{uuid.uuid4().hex[:6].upper()}"
    user_id = user["id"] if user else None

    # 2. Persist Order Header
    cursor.execute("""
        INSERT INTO orders (
            order_ref, user_id, customer_name, customer_email,
            customer_phone, subtotal, tax_amount, total_amount,
            delivery_type, delivery_address, order_status
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'Received')
    """, (
        order_ref, user_id, req.customer_name, req.customer_email.lower(),
        req.customer_phone, subtotal, tax_amount, total_amount,
        req.delivery_type, req.delivery_address
    ))
    order_id = cursor.lastrowid

    # 3. Persist Order Items with Immutable Price Snapshot
    for item in line_items_data:
        cursor.execute("""
            INSERT INTO order_items (
                order_id, item_id, item_name, unit_price_snapshot, quantity, line_total
            ) VALUES (?, ?, ?, ?, ?, ?)
        """, (
            order_id, item["item_id"], item["item_name"],
            item["unit_price_snapshot"], item["quantity"], item["line_total"]
        ))
        
    conn.commit()
    conn.close()

    return {
        "success": True,
        "order_id": order_id,
        "order_ref": order_ref,
        "subtotal": subtotal,
        "tax": tax_amount,
        "total": total_amount,
        "message": f"Order #{order_ref} confirmed! Our Ranwar bakehouse team is preparing your selection."
    }

@app.get("/api/orders")
def list_orders(user: Optional[dict] = Depends(get_current_user)):
    conn = get_connection()
    cursor = conn.cursor()
    
    if user and user["role"] == "admin":
        cursor.execute("SELECT * FROM orders ORDER BY created_at DESC")
    elif user:
        cursor.execute("SELECT * FROM orders WHERE user_id = ? OR customer_email = ? ORDER BY created_at DESC", 
                       (user["id"], user["email"]))
    else:
        conn.close()
        return []
        
    orders = []
    for order_row in cursor.fetchall():
        order_dict = dict(order_row)
        cursor_items = conn.cursor()
        cursor_items.execute("SELECT * FROM order_items WHERE order_id = ?", (order_dict["id"],))
        order_dict["items"] = [dict(it) for it in cursor_items.fetchall()]
        orders.append(order_dict)
        
    conn.close()
    return orders

@app.patch("/api/orders/{order_id}/status")
def update_order_status(order_id: int, req: StatusUpdateRequest, user: Optional[dict] = Depends(get_current_user)):
    if not user or user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Staff access required.")
        
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE orders SET order_status = ? WHERE id = ?", (req.status, order_id))
    conn.commit()
    conn.close()
    return {"success": True, "status": req.status}

@app.get("/api/stats")
def get_stats(user: Optional[dict] = Depends(get_current_user)):
    if not user or user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Staff access required.")
        
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) as total_orders, COALESCE(SUM(total_amount), 0) as total_revenue FROM orders")
    order_stats = dict(cursor.fetchone())
    
    cursor.execute("SELECT COUNT(*) as total_bookings FROM bookings WHERE status = 'Confirmed'")
    booking_stats = dict(cursor.fetchone())
    
    conn.close()
    return {
        "total_revenue": round(order_stats["total_revenue"], 2),
        "total_orders": order_stats["total_orders"],
        "active_bookings": booking_stats["total_bookings"]
    }

# HTML Pages
@app.get("/", response_class=HTMLResponse)
def index_page(request: Request):
    user = get_current_user(request)
    return templates.TemplateResponse("index.html", {"request": request, "user": user})

@app.get("/dashboard", response_class=HTMLResponse)
def dashboard_page(request: Request):
    user = get_current_user(request)
    if not user:
        return RedirectResponse(url="/?login=true")
    return templates.TemplateResponse("dashboard.html", {"request": request, "user": user})

@app.get("/staff", response_class=HTMLResponse)
def staff_page(request: Request):
    user = get_current_user(request)
    if not user or user.get("role") != "admin":
        return RedirectResponse(url="/?login=true")
    return templates.TemplateResponse("staff.html", {"request": request, "user": user})

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
