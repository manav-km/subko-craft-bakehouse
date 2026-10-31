# Subko Coffee Roasters & Craft Bakehouse — Flagship Web Platform

A production-grade, zero AI-slop full-stack application built for **Subko Coffee Roasters & Craft Bakehouse** (Mary Lodge, Ranwar Village, Bandra West, Mumbai).

---

## 1. Verified Business Details & Identity
- **Business Name**: Subko Coffee Roasters & Craft Bakehouse
- **Category**: Specialty Coffee Roastery, Craft Bakehouse & Single-Origin Cacao
- **Physical Address**: Ground Floor, Mary Lodge, 21A, Chapel Rd, Ranwar, Bandra West, Mumbai, Maharashtra 400050
- **Operating Hours**: Monday – Sunday, 07:30 AM to 10:00 PM (Daily)
- **Direct Phone**: `+91 91360 22008` (Direct click-to-call enabled)
- **Official Email**: `orders@subko.coffee`
- **Google Rating**: 4.6 ★ (4,820+ authentic reviews)
- **WhatsApp Concierge**: Integrated with pre-filled greeting

---

## 2. Core Functional Capabilities
1. **Zero AI-Slop Editorial Design**:
   - Palette derived from authentic roasted beans, raw linen canvas, aged brass, and terracotta brick.
   - Clean editorial typography (`Newsreader` serif + `Plus Jakarta Sans` grotesque).
   - Fully responsive across mobile (320px–390px), tablet (768px), and desktop (1024px–1440px+).
   - WCAG 2.2 AA compliant contrast and visible keyboard focus states.
2. **Customer Authentication & Profiles**:
   - Secure sign up with email and phone verification.
   - Salted PBKDF2 password hashing (100,000 iterations).
   - HTTP-only session cookies and JWT bearer token authentication.
   - Personal patron dashboard displaying active reservations and past orders.
3. **Table & Cupping Room Reservation Engine**:
   - Advance reservations for Cafe Tables, Cupping Room Sensory Tastings, and Private Brew Sessions.
   - Real-time conflict checks and date/time selection.
   - Generates persistent reference code (`SBK-BK-...`).
4. **Online Food Ordering & Strict Price Snapshotting**:
   - Real menu items with authentic INR prices (e.g., Riverdale Pour-Over ₹265, Butter Croissant ₹240, Podi Sourdough Toast ₹260).
   - Interactive slide-over cart drawer with live subtotal and 5% GST computation.
   - **Immutable Price Snapshots**: Every line item captures and permanently records unit price at checkout in `order_items` table.
5. **Staff Concierge & Kitchen Bar Portal (`/staff`)**:
   - Live revenue metrics, total orders, and active table reservations.
   - Real-time order dispatch management (`Received` &rarr; `Preparing` &rarr; `Ready` &rarr; `Delivered`).
   - Table seating ledger status management (`Confirmed` &rarr; `Completed` &rarr; `Cancelled`).

---

## 3. Technology Stack
- **Backend**: Python 3.14 + FastAPI (high-performance async ASGI)
- **Database**: SQLite 3 (`subko.db`) with relational integrity and foreign keys
- **Security**: PBKDF2 SHA-256 password hashing + PyJWT
- **Frontend**: Accessible Semantic HTML5, Bespoke CSS Design System, Vanilla JavaScript
- **Testing**: Automated end-to-end `pytest` suite

---

## 4. How to Run Locally

```bash
# 1. Navigate to directory
cd "D:\Manav-KM\Websites\Customer Websites\subko-craft-bakehouse"

# 2. Run automated tests
python -m pytest test_subko.py -v

# 3. Start server
python main.py
```

The application will be live at:
- **Public Flagship Website**: `http://127.0.0.1:8000/`
- **Customer Dashboard**: `http://127.0.0.1:8000/dashboard`
- **Staff Concierge Portal**: `http://127.0.0.1:8000/staff` (Staff Credentials seeded: `staff@subko.coffee` / `SubkoStaff@2026`)
