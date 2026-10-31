/* ==========================================================================
   Subko Coffee Roasters & Craft Bakehouse - Client Application Logic
   Accessible State Management, Cart & Checkout, Reservations, Auth
   ========================================================================== */

let menuItems = [];
let cart = [];
let currentUser = null;

// Initialize on DOM Ready
document.addEventListener("DOMContentLoaded", async () => {
  await checkAuthStatus();
  loadCartFromStorage();
  
  if (document.getElementById("menuGrid")) {
    await fetchMenu();
    setupCategoryTabs();
    setupBookingForm();
  }
  
  if (window.location.pathname === "/dashboard") {
    loadUserDashboard();
  }
  
  if (window.location.pathname === "/staff") {
    loadStaffPortal();
  }

  // Check URL parameters for ?login=true
  const urlParams = new URLSearchParams(window.location.search);
  if (urlParams.get("login") === "true") {
    openAuthModal();
  }
});

// Toast Helper
function showToast(msg) {
  let toast = document.getElementById("toastNotice");
  if (!toast) {
    toast = document.createElement("div");
    toast.id = "toastNotice";
    toast.className = "toast-notice";
    document.body.appendChild(toast);
  }
  toast.textContent = msg;
  toast.classList.add("show");
  setTimeout(() => toast.classList.remove("show"), 4000);
}

// Authentication Handlers
async function checkAuthStatus() {
  try {
    const res = await fetch("/api/auth/me");
    const data = await res.json();
    if (data.authenticated) {
      currentUser = data.user;
      renderUserNav();
    } else {
      currentUser = null;
      renderGuestNav();
    }
  } catch (err) {
    currentUser = null;
  }
}

function renderUserNav() {
  const container = document.getElementById("navAuthContainer");
  if (!container) return;
  
  let staffLink = currentUser.role === "admin" 
    ? `<a href="/staff" class="btn btn-secondary" style="font-size:0.8rem; padding:0.4rem 0.8rem;">Staff Portal</a>` 
    : "";
    
  container.innerHTML = `
    ${staffLink}
    <a href="/dashboard" class="btn btn-secondary" style="font-size:0.85rem; padding:0.4rem 0.8rem;">
      <span>Account</span> (${currentUser.full_name.split(" ")[0]})
    </a>
    <button onclick="handleLogout()" class="btn btn-secondary" style="font-size:0.85rem; padding:0.4rem 0.8rem;">Logout</button>
  `;
}

function renderGuestNav() {
  const container = document.getElementById("navAuthContainer");
  if (!container) return;
  container.innerHTML = `
    <button onclick="openAuthModal()" class="btn btn-secondary" style="font-size:0.85rem; padding:0.4rem 0.9rem;">Sign In / Join</button>
  `;
}

function openAuthModal() {
  const modal = document.getElementById("authModal");
  if (modal) modal.classList.add("active");
}

function closeAuthModal() {
  const modal = document.getElementById("authModal");
  if (modal) modal.classList.remove("active");
}

function switchAuthTab(tab) {
  const loginForm = document.getElementById("loginForm");
  const registerForm = document.getElementById("registerForm");
  const tabLogin = document.getElementById("tabLoginBtn");
  const tabRegister = document.getElementById("tabRegisterBtn");
  
  if (tab === "login") {
    loginForm.style.display = "block";
    registerForm.style.display = "none";
    tabLogin.classList.add("active");
    tabRegister.classList.remove("active");
  } else {
    loginForm.style.display = "none";
    registerForm.style.display = "block";
    tabLogin.classList.remove("active");
    tabRegister.classList.add("active");
  }
}

async function handleLogin(e) {
  e.preventDefault();
  const email = document.getElementById("loginEmail").value;
  const password = document.getElementById("loginPassword").value;
  
  try {
    const res = await fetch("/api/auth/login", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email, password })
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || "Login failed");
    
    currentUser = data.user;
    closeAuthModal();
    renderUserNav();
    showToast(`Welcome back, ${currentUser.full_name}!`);
    if (window.location.search.includes("login=true")) {
      window.location.href = currentUser.role === "admin" ? "/staff" : "/dashboard";
    }
  } catch (err) {
    alert(err.message);
  }
}

async function handleRegister(e) {
  e.preventDefault();
  const full_name = document.getElementById("regName").value;
  const email = document.getElementById("regEmail").value;
  const phone = document.getElementById("regPhone").value;
  const password = document.getElementById("regPassword").value;
  
  try {
    const res = await fetch("/api/auth/register", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ full_name, email, phone, password })
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || "Registration failed");
    
    currentUser = data.user;
    closeAuthModal();
    renderUserNav();
    showToast(`Account created! Welcome to Subko, ${currentUser.full_name}.`);
  } catch (err) {
    alert(err.message);
  }
}

async function handleLogout() {
  try {
    await fetch("/api/auth/logout", { method: "POST" });
    currentUser = null;
    renderGuestNav();
    showToast("Signed out successfully.");
    if (window.location.pathname !== "/") {
      window.location.href = "/";
    }
  } catch (err) {
    console.error(err);
  }
}

// Menu Loading & Rendering
async function fetchMenu() {
  try {
    const res = await fetch("/api/menu");
    menuItems = await res.json();
    renderMenuGrid(menuItems);
  } catch (err) {
    console.error("Could not load menu", err);
  }
}

function renderMenuGrid(items) {
  const grid = document.getElementById("menuGrid");
  if (!grid) return;
  
  if (items.length === 0) {
    grid.innerHTML = `<p style="grid-column: 1/-1; text-align:center; padding: 2rem;">No items found in this collection.</p>`;
    return;
  }
  
  grid.innerHTML = items.map(item => `
    <article class="menu-card" data-category="${item.category}">
      <div class="menu-card-top">
        <div class="menu-meta">
          <span class="menu-tag">${item.category}</span>
          <span class="menu-diet">${item.dietary}</span>
        </div>
        <h4 class="menu-title">${item.name}</h4>
        <p class="menu-desc">${item.description}</p>
      </div>
      <div class="menu-card-bottom">
        <span class="menu-price">₹${item.price.toFixed(0)}</span>
        <button class="btn btn-primary" onclick="addToCart(${item.id})">
          <span>+ Add to Order</span>
        </button>
      </div>
    </article>
  `).join("");
}

function setupCategoryTabs() {
  const tabs = document.querySelectorAll(".tab-btn");
  tabs.forEach(tab => {
    tab.addEventListener("click", () => {
      tabs.forEach(t => t.classList.remove("active"));
      tab.classList.add("active");
      const cat = tab.getAttribute("data-category");
      if (cat === "all") {
        renderMenuGrid(menuItems);
      } else {
        const filtered = menuItems.filter(item => item.category === cat);
        renderMenuGrid(filtered);
      }
    });
  });
}

// Cart Drawer & Local Storage Management
function loadCartFromStorage() {
  const saved = localStorage.getItem("subko_cart");
  if (saved) {
    try { cart = JSON.parse(saved); } catch (e) { cart = []; }
  }
  updateCartBadge();
}

function saveCartToStorage() {
  localStorage.setItem("subko_cart", JSON.stringify(cart));
  updateCartBadge();
}

function updateCartBadge() {
  const badge = document.getElementById("cartCountBadge");
  const totalQty = cart.reduce((acc, it) => acc + it.quantity, 0);
  if (badge) {
    badge.textContent = totalQty;
  }
}

function toggleCartDrawer() {
  const drawer = document.getElementById("cartDrawer");
  const backdrop = document.getElementById("cartBackdrop");
  if (!drawer || !backdrop) return;
  
  const isActive = drawer.classList.contains("active");
  if (isActive) {
    drawer.classList.remove("active");
    backdrop.classList.remove("active");
  } else {
    renderCartDrawerItems();
    drawer.classList.add("active");
    backdrop.classList.add("active");
  }
}

function addToCart(itemId) {
  const item = menuItems.find(m => m.id === itemId);
  if (!item) return;
  
  const existing = cart.find(c => c.itemId === itemId);
  if (existing) {
    existing.quantity += 1;
  } else {
    cart.push({
      itemId: item.id,
      name: item.name,
      price: item.price,
      quantity: 1
    });
  }
  saveCartToStorage();
  showToast(`Added ${item.name} to order.`);
  toggleCartDrawer();
}

function updateCartQty(itemId, delta) {
  const idx = cart.findIndex(c => c.itemId === itemId);
  if (idx === -1) return;
  
  cart[idx].quantity += delta;
  if (cart[idx].quantity <= 0) {
    cart.splice(idx, 1);
  }
  saveCartToStorage();
  renderCartDrawerItems();
}

function renderCartDrawerItems() {
  const container = document.getElementById("cartItemsList");
  const subtotalEl = document.getElementById("cartSubtotal");
  const taxEl = document.getElementById("cartTax");
  const totalEl = document.getElementById("cartTotal");
  const checkoutBtn = document.getElementById("checkoutBtn");
  
  if (!container) return;
  
  if (cart.length === 0) {
    container.innerHTML = `<p style="text-align: center; color: var(--color-charcoal-500); padding: 3rem 0;">Your craft bakehouse tray is currently empty.</p>`;
    subtotalEl.textContent = "₹0.00";
    taxEl.textContent = "₹0.00";
    totalEl.textContent = "₹0.00";
    if (checkoutBtn) checkoutBtn.disabled = true;
    return;
  }
  
  let subtotal = 0;
  container.innerHTML = cart.map(it => {
    const lineTotal = it.price * it.quantity;
    subtotal += lineTotal;
    return `
      <div class="cart-item-row">
        <div class="cart-item-info">
          <strong>${it.name}</strong>
          <span>₹${it.price.toFixed(0)} × ${it.quantity}</span>
        </div>
        <div class="cart-qty-ctrl">
          <button class="qty-btn" onclick="updateCartQty(${it.itemId}, -1)">−</button>
          <span style="font-size:0.9rem; font-weight:700;">${it.quantity}</span>
          <button class="qty-btn" onclick="updateCartQty(${it.itemId}, 1)">+</button>
        </div>
      </div>
    `;
  }).join("");
  
  const tax = subtotal * 0.05; // 5% GST
  const grandTotal = subtotal + tax;
  
  subtotalEl.textContent = `₹${subtotal.toFixed(2)}`;
  taxEl.textContent = `₹${tax.toFixed(2)}`;
  totalEl.textContent = `₹${grandTotal.toFixed(2)}`;
  if (checkoutBtn) checkoutBtn.disabled = false;
}

// Checkout & Immutable Price Snapshot Dispatch
async function handleCheckout() {
  if (cart.length === 0) return;
  
  // Prompt or use authenticated details
  let name = currentUser ? currentUser.full_name : prompt("Please enter your name for the order receipt:");
  if (!name) return;
  
  let email = currentUser ? currentUser.email : prompt("Please enter your email for order confirmation:");
  if (!email) return;
  
  let phone = currentUser ? currentUser.phone : prompt("Please enter your 10-digit mobile number:");
  if (!phone) return;
  
  const deliveryType = document.getElementById("deliveryTypeSelect") 
    ? document.getElementById("deliveryTypeSelect").value 
    : "Dine-in Pick-up";
    
  const payload = {
    customer_name: name,
    customer_email: email,
    customer_phone: phone,
    delivery_type: deliveryType,
    delivery_address: "Subko Ranwar Flagship Counter",
    items: cart.map(c => ({ item_id: c.itemId, quantity: c.quantity }))
  };
  
  try {
    const res = await fetch("/api/orders", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || "Checkout failed");
    
    // Clear cart
    cart = [];
    saveCartToStorage();
    toggleCartDrawer();
    
    alert(`Order Confirmed!\nReference: #${data.order_ref}\nTotal: ₹${data.total}\n\nItem price snapshots and 5% GST receipt have been recorded in the persistent database.`);
    if (currentUser) {
      window.location.href = "/dashboard";
    }
  } catch (err) {
    alert("Error placing order: " + err.message);
  }
}

// Table & Experience Booking Form
function setupBookingForm() {
  const form = document.getElementById("tableBookingForm");
  if (!form) return;
  
  // Auto-fill if user logged in
  if (currentUser) {
    document.getElementById("bookName").value = currentUser.full_name;
    document.getElementById("bookEmail").value = currentUser.email;
    document.getElementById("bookPhone").value = currentUser.phone;
  }
  
  // Set min date to today
  const dateInput = document.getElementById("bookDate");
  if (dateInput) {
    const today = new Date().toISOString().split("T")[0];
    dateInput.min = today;
    dateInput.value = today;
  }
  
  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    const payload = {
      customer_name: document.getElementById("bookName").value,
      customer_email: document.getElementById("bookEmail").value,
      customer_phone: document.getElementById("bookPhone").value,
      reservation_date: document.getElementById("bookDate").value,
      reservation_time: document.getElementById("bookTime").value,
      guests_count: parseInt(document.getElementById("bookGuests").value, 10),
      service_type: document.getElementById("bookServiceType").value,
      special_notes: document.getElementById("bookNotes").value
    };
    
    try {
      const res = await fetch("/api/bookings", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload)
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || "Booking failed");
      
      alert(`Reservation Confirmed!\nBooking Reference: ${data.booking_ref}\nWe look forward to welcoming you at Mary Lodge, Ranwar Village.`);
      form.reset();
      if (currentUser) {
        window.location.href = "/dashboard";
      }
    } catch (err) {
      alert("Error creating reservation: " + err.message);
    }
  });
}

// Dashboard Page Population
async function loadUserDashboard() {
  try {
    // 1. Fetch Bookings
    const bRes = await fetch("/api/bookings");
    const bookings = await bRes.json();
    const bList = document.getElementById("userBookingsList");
    if (bList) {
      if (bookings.length === 0) {
        bList.innerHTML = `<p style="color:var(--color-charcoal-500);">No active reservations found. <a href="/#reserve" style="color:var(--color-terracotta); font-weight:600;">Reserve a table or cupping session</a>.</p>`;
      } else {
        bList.innerHTML = bookings.map(b => `
          <div style="background:#fff; border:1px solid var(--color-cream-300); border-radius:var(--radius-md); padding:1.25rem; margin-bottom:1rem;">
            <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:0.5rem;">
              <strong style="font-family:var(--font-serif); font-size:1.15rem; color:var(--color-espresso-900);">${b.booking_ref}</strong>
              <span class="status-pill" style="margin:0;">${b.status}</span>
            </div>
            <p style="font-size:0.9rem; color:var(--color-charcoal-700); margin-bottom:0.25rem;">
              <strong>${b.service_type}</strong> for ${b.guests_count} guest(s)
            </p>
            <p style="font-size:0.85rem; color:var(--color-charcoal-500);">
              Date: <strong>${b.reservation_date}</strong> at <strong>${b.reservation_time}</strong> | Venue: Mary Lodge, Ranwar Village, Bandra
            </p>
          </div>
        `).join("");
      }
    }

    // 2. Fetch Orders with Price Snapshot receipts
    const oRes = await fetch("/api/orders");
    const orders = await oRes.json();
    const oList = document.getElementById("userOrdersList");
    if (oList) {
      if (orders.length === 0) {
        oList.innerHTML = `<p style="color:var(--color-charcoal-500);">No orders placed yet. <a href="/#menu" style="color:var(--color-terracotta); font-weight:600;">Explore our craft bakehouse offerings</a>.</p>`;
      } else {
        oList.innerHTML = orders.map(o => `
          <div style="background:#fff; border:1px solid var(--color-cream-300); border-radius:var(--radius-md); padding:1.25rem; margin-bottom:1rem;">
            <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:0.5rem;">
              <strong style="font-family:var(--font-serif); font-size:1.15rem; color:var(--color-espresso-900);">Order #${o.order_ref}</strong>
              <span class="status-pill" style="margin:0;">${o.order_status}</span>
            </div>
            <p style="font-size:0.85rem; color:var(--color-charcoal-500); margin-bottom:0.75rem;">
              Placed on: ${new Date(o.created_at).toLocaleString()} | ${o.delivery_type}
            </p>
            <div style="background:var(--color-cream-100); padding:0.75rem; border-radius:var(--radius-sm); margin-bottom:0.75rem;">
              <div style="font-size:0.8rem; font-weight:700; text-transform:uppercase; color:var(--color-charcoal-500); margin-bottom:0.4rem;">Itemized Snapshot (Immutable Checkout Rates)</div>
              ${(o.items || []).map(it => `
                <div style="display:flex; justify-content:space-between; font-size:0.88rem; margin-bottom:0.25rem;">
                  <span>${it.item_name} × ${it.quantity}</span>
                  <strong>₹${it.line_total.toFixed(2)} (@ ₹${it.unit_price_snapshot.toFixed(0)})</strong>
                </div>
              `).join("")}
              <div style="border-top:1px dashed var(--color-cream-300); margin-top:0.5rem; padding-top:0.5rem; display:flex; justify-content:space-between; font-size:0.9rem;">
                <span>GST (5%): ₹${o.tax_amount.toFixed(2)}</span>
                <span style="font-weight:700; color:var(--color-espresso-900);">Total: ₹${o.total_amount.toFixed(2)}</span>
              </div>
            </div>
          </div>
        `).join("");
      }
    }
  } catch (err) {
    console.error(err);
  }
}

// Staff Portal Real-time Management
async function loadStaffPortal() {
  try {
    // 1. Stats
    const sRes = await fetch("/api/stats");
    const stats = await sRes.json();
    if (document.getElementById("statRev")) document.getElementById("statRev").textContent = `₹${stats.total_revenue.toLocaleString()}`;
    if (document.getElementById("statOrders")) document.getElementById("statOrders").textContent = stats.total_orders;
    if (document.getElementById("statBookings")) document.getElementById("statBookings").textContent = stats.active_bookings;
    
    // 2. Orders
    const oRes = await fetch("/api/orders");
    const orders = await oRes.json();
    const staffOrders = document.getElementById("staffOrdersTable");
    if (staffOrders) {
      staffOrders.innerHTML = orders.map(o => `
        <tr>
          <td><strong>#${o.order_ref}</strong></td>
          <td>${o.customer_name}<br><small>${o.customer_phone}</small></td>
          <td>
            ${(o.items || []).map(it => `${it.item_name} (×${it.quantity})`).join(", ")}
          </td>
          <td><strong>₹${o.total_amount.toFixed(2)}</strong></td>
          <td><span class="badge-batch">${o.order_status}</span></td>
          <td>
            <select onchange="updateStaffOrderStatus(${o.id}, this.value)" class="form-control" style="font-size:0.8rem; padding:0.2rem 0.5rem; height:auto;">
              <option value="Received" ${o.order_status === "Received" ? "selected" : ""}>Received</option>
              <option value="Preparing" ${o.order_status === "Preparing" ? "selected" : ""}>Preparing</option>
              <option value="Ready" ${o.order_status === "Ready" ? "selected" : ""}>Ready</option>
              <option value="Delivered" ${o.order_status === "Delivered" ? "selected" : ""}>Delivered</option>
            </select>
          </td>
        </tr>
      `).join("");
    }

    // 3. Bookings
    const bRes = await fetch("/api/bookings");
    const bookings = await bRes.json();
    const staffBookings = document.getElementById("staffBookingsTable");
    if (staffBookings) {
      staffBookings.innerHTML = bookings.map(b => `
        <tr>
          <td><strong>${b.booking_ref}</strong></td>
          <td>${b.customer_name}<br><small>${b.customer_phone}</small></td>
          <td>${b.service_type} (${b.guests_count} Guests)</td>
          <td>${b.reservation_date} @ ${b.reservation_time}</td>
          <td><span class="badge-batch">${b.status}</span></td>
          <td>
            <select onchange="updateStaffBookingStatus(${b.id}, this.value)" class="form-control" style="font-size:0.8rem; padding:0.2rem 0.5rem; height:auto;">
              <option value="Confirmed" ${b.status === "Confirmed" ? "selected" : ""}>Confirmed</option>
              <option value="Completed" ${b.status === "Completed" ? "selected" : ""}>Completed</option>
              <option value="Cancelled" ${b.status === "Cancelled" ? "selected" : ""}>Cancelled</option>
            </select>
          </td>
        </tr>
      `).join("");
    }
  } catch (err) {
    console.error(err);
  }
}

async function updateStaffOrderStatus(id, newStatus) {
  try {
    await fetch(`/api/orders/${id}/status`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ status: newStatus })
    });
    showToast("Order status updated.");
    loadStaffPortal();
  } catch (err) {
    alert("Could not update order: " + err.message);
  }
}

async function updateStaffBookingStatus(id, newStatus) {
  try {
    await fetch(`/api/bookings/${id}/status`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ status: newStatus })
    });
    showToast("Booking status updated.");
    loadStaffPortal();
  } catch (err) {
    alert("Could not update booking: " + err.message);
  }
}
