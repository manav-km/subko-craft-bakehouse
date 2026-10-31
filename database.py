import sqlite3
import os
import hashlib
import binascii

DB_PATH = os.path.join(os.path.dirname(__file__), "subko.db")

def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def hash_password(password: str, salt: str = None) -> str:
    if salt is None:
        salt = binascii.hexlify(os.urandom(16)).decode('utf-8')
    pwd_hash = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt.encode('utf-8'), 100000)
    return f"{salt}${binascii.hexlify(pwd_hash).decode('utf-8')}"

def verify_password(stored_password: str, provided_password: str) -> bool:
    try:
        salt, expected_hash = stored_password.split('$')
        pwd_hash = hashlib.pbkdf2_hmac('sha256', provided_password.encode('utf-8'), salt.encode('utf-8'), 100000)
        return binascii.hexlify(pwd_hash).decode('utf-8') == expected_hash
    except Exception:
        return False

def init_db():
    conn = get_connection()
    cursor = conn.cursor()
    
    # 1. Users Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        full_name TEXT NOT NULL,
        email TEXT UNIQUE NOT NULL,
        phone TEXT NOT NULL,
        password_hash TEXT NOT NULL,
        role TEXT DEFAULT 'customer',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)

    # 2. Menu Items Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS menu_items (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        category TEXT NOT NULL,
        name TEXT NOT NULL,
        description TEXT NOT NULL,
        price REAL NOT NULL,
        dietary TEXT NOT NULL,
        prep_time_mins INTEGER DEFAULT 15,
        is_available BOOLEAN DEFAULT 1
    )
    """)

    # 3. Bookings Table (Table & Cupping Sessions)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS bookings (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        booking_ref TEXT UNIQUE NOT NULL,
        user_id INTEGER,
        customer_name TEXT NOT NULL,
        customer_email TEXT NOT NULL,
        customer_phone TEXT NOT NULL,
        reservation_date TEXT NOT NULL,
        reservation_time TEXT NOT NULL,
        guests_count INTEGER NOT NULL,
        service_type TEXT NOT NULL,
        special_notes TEXT,
        status TEXT DEFAULT 'Confirmed',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(user_id) REFERENCES users(id)
    )
    """)

    # 4. Orders Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS orders (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        order_ref TEXT UNIQUE NOT NULL,
        user_id INTEGER,
        customer_name TEXT NOT NULL,
        customer_email TEXT NOT NULL,
        customer_phone TEXT NOT NULL,
        subtotal REAL NOT NULL,
        tax_amount REAL NOT NULL,
        total_amount REAL NOT NULL,
        delivery_type TEXT NOT NULL,
        delivery_address TEXT,
        order_status TEXT DEFAULT 'Received',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(user_id) REFERENCES users(id)
    )
    """)

    # 5. Order Items Table (Immutable Price Snapshots)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS order_items (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        order_id INTEGER NOT NULL,
        item_id INTEGER NOT NULL,
        item_name TEXT NOT NULL,
        unit_price_snapshot REAL NOT NULL,
        quantity INTEGER NOT NULL,
        line_total REAL NOT NULL,
        FOREIGN KEY(order_id) REFERENCES orders(id),
        FOREIGN KEY(item_id) REFERENCES menu_items(id)
    )
    """)

    # Check if menu items exist, if not seed verified menu
    cursor.execute("SELECT COUNT(*) as count FROM menu_items")
    if cursor.fetchone()["count"] == 0:
        verified_items = [
            # Specialty Coffees
            ("Specialty Coffee", "Riverdale Estate Pour-Over", "Washed Arabica from Shevaroy Hills. Vibrant notes of mandarin orange, jasmine floral, and clean honey finish.", 265.0, "Vegan", 8),
            ("Specialty Coffee", "Subko 18-Hour Cold Brew", "Slow-steeped Arabica micro-lot with subtle notes of dark cocoa nibs and candied plum.", 285.0, "Vegan", 3),
            ("Specialty Coffee", "Flat White (Double Ristretto)", "Velvety textured whole milk poured over a rich double ristretto extraction.", 250.0, "Vegetarian", 6),
            ("Specialty Coffee", "Cortado", "1:1 ratio of rich espresso and silky textured steamed milk in a fluted glass.", 230.0, "Vegetarian", 5),
            ("Specialty Coffee", "Iced Filter Coffee Kaapi Tonic", "Traditional South Indian chicory blend elevated with craft tonic water and citrus peel.", 270.0, "Vegan", 4),
            
            # Craft Bakehouse
            ("Craft Bakehouse", "Classic Butter Sourdough Croissant", "72-hour slow-fermented French cultured butter lamination with honeycomb open crumb.", 240.0, "Vegetarian", 5),
            ("Craft Bakehouse", "Pain Au Chocolat", "Double batons of single-origin 65% Podi cacao enveloped in crisp, flaky pastry.", 275.0, "Vegetarian", 5),
            ("Craft Bakehouse", "Almond Frangipane Croissant", "Twice-baked croissant filled with house-ground almond cream and topped with toasted flaked almonds.", 320.0, "Vegetarian", 6),
            ("Craft Bakehouse", "Sourdough Toast with Gunpowder Podi", "Toasted country sourdough batard slathered with cultured A2 ghee and spicy house-milled podi.", 260.0, "Vegetarian", 8),
            ("Craft Bakehouse", "Anamalai Cacao Babka Knot", "Pillowy brioche dough braided with rich single-origin dark chocolate ganache and spiced cardamom syrup.", 290.0, "Vegetarian", 5),
            ("Craft Bakehouse", "Jalapeno & Cream Cheese Sourdough Bagel", "Boiled and baked fresh every morning, served warm with whipped herbed cream cheese.", 295.0, "Vegetarian", 7),
            
            # Desserts & Craft Cacao
            ("Desserts & Craft Cacao", "Subko Signature Salted Caramel Chocolate Tart", "Dark chocolate sablé crust, gooey sea-salt caramel layer, and 70% dark chocolate ganache.", 340.0, "Vegetarian", 4),
            ("Desserts & Craft Cacao", "Basque Burnt Cheesecake Slice", "Caramelized charred exterior with a rich, molten cream cheese center made with pure vanilla pod.", 360.0, "Vegetarian", 4),
            ("Desserts & Craft Cacao", "Morning Cinnamon Cardamom Bun", "Fluffy rolled brioche coated in wild forest cinnamon, brown muscovado sugar, and crushed green cardamom.", 210.0, "Vegetarian", 4)
        ]
        cursor.executemany("""
            INSERT INTO menu_items (category, name, description, price, dietary, prep_time_mins)
            VALUES (?, ?, ?, ?, ?, ?)
        """, verified_items)

    # Seed Admin / Staff Account if not exists
    cursor.execute("SELECT id FROM users WHERE email = 'staff@subko.coffee'")
    if not cursor.fetchone():
        admin_pass = hash_password("SubkoStaff@2026")
        cursor.execute("""
            INSERT INTO users (full_name, email, phone, password_hash, role)
            VALUES (?, ?, ?, ?, ?)
        """, ("Subko Ranwar Staff", "staff@subko.coffee", "+919136022008", admin_pass, "admin"))

    conn.commit()
    conn.close()

if __name__ == "__main__":
    init_db()
    print("Database initialized successfully at", DB_PATH)
