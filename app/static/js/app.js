/* Dress 2 Decor — AI Automation Dashboard Frontend */

document.addEventListener("DOMContentLoaded", () => {
    const state = {
        revenueChart: null,
        statusChart: null,
        calendarStart: getMonday(new Date()),
    };

    initNavigation();
    initClock();
    initChat();
    initFilters();
    initMeetings();
    loadHealth();
    loadDashboard();
});

// ── Utilities ────────────────────────────────────────────────────

function getMonday(d) {
    const dt = new Date(d);
    const day = dt.getDay();
    const diff = dt.getDate() - day + (day === 0 ? -6 : 1);
    dt.setDate(diff);
    dt.setHours(0, 0, 0, 0);
    return dt;
}

function fmtDate(d) {
    const y = d.getFullYear();
    const m = String(d.getMonth() + 1).padStart(2, "0");
    const day = String(d.getDate()).padStart(2, "0");
    return `${y}-${m}-${day}`;
}

function escapeHtml(str) {
    if (str === null || str === undefined) return "";
    return String(str)
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;");
}

function statusBadge(status) {
    const map = {
        pending: "bg-warning text-dark",
        confirmed: "bg-info text-dark",
        processing: "bg-primary",
        shipped: "bg-secondary",
        delivered: "bg-success",
        cancelled: "bg-danger",
        returned: "bg-dark",
        paid: "bg-success",
        failed: "bg-danger",
        refunded: "bg-secondary",
        scheduled: "bg-primary",
        completed: "bg-success",
    };
    const cls = map[(status || "").toLowerCase()] || "bg-secondary";
    return `<span class="badge ${cls}">${escapeHtml(status)}</span>`;
}

async function fetchJson(url, options = {}) {
    const res = await fetch(url, options);
    if (!res.ok) {
        let detail = res.statusText;
        try {
            const err = await res.json();
            detail = err.detail || detail;
        } catch (_) {}
        throw new Error(detail);
    }
    return res.json();
}

// ── Navigation & Clock ───────────────────────────────────────────

function initNavigation() {
    const navLinks = document.querySelectorAll("[data-section]");
    const titles = {
        dashboard: "Dashboard",
        chat: "AI Assistant",
        orders: "Order Management",
        vendors: "Vendor Management",
        products: "Product Catalog",
        meetings: "Meetings & Calendar",
        activity: "Automation Activity Log",
    };

    navLinks.forEach((el) => {
        el.addEventListener("click", (e) => {
            e.preventDefault();
            const target = el.getAttribute("data-section");
            switchSection(target, titles[target] || "Dashboard");
        });
    });

    const toggle = document.getElementById("sidebar-toggle");
    if (toggle) {
        toggle.addEventListener("click", () => {
            document.getElementById("sidebar").classList.toggle("show");
        });
    }
}

function switchSection(section, title) {
    document.querySelectorAll(".sidebar .nav-link").forEach((l) => {
        l.classList.toggle("active", l.getAttribute("data-section") === section);
    });
    document.querySelectorAll(".content-section").forEach((s) => {
        s.classList.toggle("active", s.id === `section-${section}`);
    });
    document.getElementById("page-title").textContent = title;
    document.getElementById("sidebar").classList.remove("show");

    if (section === "dashboard") loadDashboard();
    else if (section === "orders") loadOrders();
    else if (section === "vendors") loadVendors();
    else if (section === "products") loadProducts();
    else if (section === "meetings") loadMeetings();
    else if (section === "activity") loadActivities();
}

function initClock() {
    const el = document.getElementById("current-time");
    const update = () => {
        if (el) el.textContent = new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
    };
    update();
    setInterval(update, 30000);
}

async function loadHealth() {
    try {
        const data = await fetchJson("/api/health");
        const badge = document.getElementById("ai-status");
        if (badge) {
            badge.textContent = `AI: ${data.ai_provider.toUpperCase()}`;
        }
    } catch (_) {}
}

// ── Dashboard ────────────────────────────────────────────────────

async function loadDashboard() {
    try {
        const [stats, ordersData] = await Promise.all([
            fetchJson("/api/stats"),
            fetchJson("/api/orders?limit=10"),
        ]);

        document.getElementById("stat-orders").textContent = stats.total_orders ?? 0;
        document.getElementById("stat-revenue").textContent =
            "$" + Number(stats.total_revenue ?? 0).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 });
        document.getElementById("stat-vendors").textContent = stats.active_vendors ?? stats.total_vendors ?? 0;
        document.getElementById("stat-products").textContent = stats.total_products ?? 0;

        renderRevenueChart(stats.revenue_by_month || []);
        renderStatusChart(stats.orders_by_status || {});
        renderRecentOrders(ordersData.orders || []);
    } catch (err) {
        console.error("Dashboard load error:", err);
    }
}

function renderRevenueChart(monthly) {
    const ctx = document.getElementById("revenueChart");
    if (!ctx) return;
    if (window._revenueChart) window._revenueChart.destroy();

    window._revenueChart = new Chart(ctx, {
        type: "line",
        data: {
            labels: monthly.map((m) => m.month),
            datasets: [{
                label: "Revenue ($)",
                data: monthly.map((m) => m.revenue),
                borderColor: "#0d6efd",
                backgroundColor: "rgba(13, 110, 253, 0.12)",
                tension: 0.35,
                fill: true,
            }],
        },
        options: {
            responsive: true,
            plugins: { legend: { display: false } },
            scales: { y: { beginAtZero: true } },
        },
    });
}

function renderStatusChart(byStatus) {
    const ctx = document.getElementById("statusChart");
    if (!ctx) return;
    if (window._statusChart) window._statusChart.destroy();

    const labels = Object.keys(byStatus);
    const values = Object.values(byStatus);
    window._statusChart = new Chart(ctx, {
        type: "doughnut",
        data: {
            labels,
            datasets: [{
                data: values,
                backgroundColor: ["#ffc107", "#0dcaf0", "#0d6efd", "#6c757d", "#198754", "#dc3545", "#212529"],
            }],
        },
        options: { responsive: true, plugins: { legend: { position: "bottom" } } },
    });
}

function renderRecentOrders(orders) {
    const tbody = document.getElementById("recent-orders-body");
    if (!tbody) return;
    if (!orders.length) {
        tbody.innerHTML = `<tr><td colspan="5" class="text-center py-4 text-muted">No orders found.</td></tr>`;
        return;
    }
    tbody.innerHTML = orders
        .map((o) => `
            <tr class="cursor-pointer" onclick="openOrderModal('${escapeHtml(o.order_number)}')">
                <td class="fw-semibold text-primary">${escapeHtml(o.order_number)}</td>
                <td>${escapeHtml(o.customer_name || "N/A")}</td>
                <td>${statusBadge(o.status)}</td>
                <td>$${Number(o.total_amount || 0).toFixed(2)}</td>
                <td>${escapeHtml((o.created_at || "").slice(0, 10))}</td>
            </tr>
        `).join("");
}

// ── AI Chat ──────────────────────────────────────────────────────

function initChat() {
    const selector = document.getElementById("agent-selector");
    const vendorInput = document.getElementById("vendor-id-input");
    const chatInput = document.getElementById("chat-input");
    const sendBtn = document.getElementById("chat-send");

    if (selector && vendorInput) {
        selector.addEventListener("change", () => {
            vendorInput.classList.toggle("d-none", selector.value !== "vendor");
        });
    }

    if (sendBtn) sendBtn.addEventListener("click", sendChatMessage);
    if (chatInput) {
        chatInput.addEventListener("keydown", (e) => {
            if (e.key === "Enter") sendChatMessage();
        });
    }

    document.querySelectorAll(".quick-prompt").forEach((btn) => {
        btn.addEventListener("click", () => {
            const prompt = btn.getAttribute("data-prompt");
            const agent = btn.getAttribute("data-agent");
            if (selector && agent) {
                selector.value = agent;
                vendorInput.classList.toggle("d-none", agent !== "vendor");
                if (agent === "vendor" && !vendorInput.value) vendorInput.value = "1";
            }
            chatInput.value = prompt;
            sendChatMessage();
        });
    });
}

const _chatSessionId = "sess-" + Math.random().toString(36).slice(2, 10);

async function sendChatMessage() {
    const chatInput = document.getElementById("chat-input");
    const selector = document.getElementById("agent-selector");
    const vendorInput = document.getElementById("vendor-id-input");

    const message = chatInput.value.trim();
    if (!message) return;

    const selectedAgent = selector ? selector.value : null;
    let parsedVendorId = null;
    if (selectedAgent === "vendor") {
        parsedVendorId = parseInt(vendorInput?.value || "", 10);
        if (!vendorInput?.value || isNaN(parsedVendorId) || parsedVendorId <= 0) {
            appendChatBubble("bot", `<span class="text-danger">Please enter your Vendor ID (1 or higher) before sending a message to the Vendor Agent.</span>`);
            vendorInput?.focus();
            return;
        }
    }

    appendChatBubble("user", escapeHtml(message));
    chatInput.value = "";

    const typingId = "typing-" + Date.now();
    appendChatBubble("bot", `<span class="spinner-border spinner-border-sm me-2"></span>Thinking…`, typingId);

    const payload = {
        message,
        agent_type: selectedAgent,
        session_id: _chatSessionId,
    };
    if (selectedAgent === "vendor" && parsedVendorId) {
        payload.vendor_id = parsedVendorId;
    }

    try {
        const data = await fetchJson("/api/chat", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(payload),
        });
        document.getElementById(typingId)?.remove();

        let html = `<div class="small text-muted mb-1">[${escapeHtml(data.agent)}]</div>`;
        html += `<div>${escapeHtml(data.response).replace(/\n/g, "<br>")}</div>`;

        if (data.tool_results && data.tool_results.length > 0) {
            const collapseId = "tools-" + Date.now();
            html += `
                <div class="mt-2">
                    <a class="small text-decoration-none" data-bs-toggle="collapse" href="#${collapseId}">
                        <i class="bi bi-wrench me-1"></i>Tool Execution (${data.tool_results.length})
                    </a>
                    <div class="collapse" id="${collapseId}">
                        <div class="tool-result-box">${escapeHtml(JSON.stringify(data.tool_results, null, 2))}</div>
                    </div>
                </div>
            `;
        }
        appendChatBubble("bot", html);
    } catch (err) {
        document.getElementById(typingId)?.remove();
        appendChatBubble("bot", `<span class="text-danger">Error: ${escapeHtml(err.message)}</span>`);
    }
}

function appendChatBubble(role, htmlContent, id = null) {
    const container = document.getElementById("chat-messages");
    const div = document.createElement("div");
    div.className = `chat-bubble ${role}`;
    if (id) div.id = id;
    const now = new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
    div.innerHTML = `<div class="bubble-content">${htmlContent}</div><div class="bubble-time">${now}</div>`;
    container.appendChild(div);
    container.scrollTop = container.scrollHeight;
}

// ── Orders ───────────────────────────────────────────────────────

function initFilters() {
    document.getElementById("order-status-filter")?.addEventListener("change", loadOrders);
    document.getElementById("order-search")?.addEventListener("input", loadOrders);
    document.getElementById("product-category-filter")?.addEventListener("change", loadProducts);
    document.getElementById("product-search")?.addEventListener("input", loadProducts);
    document.getElementById("refresh-activity")?.addEventListener("click", loadActivities);
}

async function loadOrders() {
    const status = document.getElementById("order-status-filter")?.value || "";
    const search = document.getElementById("order-search")?.value || "";
    const params = new URLSearchParams();
    if (status) params.set("status", status);
    if (search) params.set("search", search);

    const tbody = document.getElementById("orders-table-body");
    try {
        const data = await fetchJson(`/api/orders?${params.toString()}`);
        const orders = data.orders || [];
        document.getElementById("orders-count").textContent = `${orders.length} orders`;
        if (!orders.length) {
            tbody.innerHTML = `<tr><td colspan="7" class="text-center py-4 text-muted">No matching orders.</td></tr>`;
            return;
        }
        tbody.innerHTML = orders.map((o) => `
            <tr>
                <td class="fw-semibold">${escapeHtml(o.order_number)}</td>
                <td>${escapeHtml(o.customer_name || "N/A")}</td>
                <td>${escapeHtml(o.customer_email || "")}</td>
                <td>${statusBadge(o.status)}</td>
                <td class="text-end">$${Number(o.total_amount || 0).toFixed(2)}</td>
                <td>${escapeHtml((o.created_at || "").slice(0, 10))}</td>
                <td class="text-end">
                    <button class="btn btn-sm btn-outline-primary" onclick="openOrderModal('${escapeHtml(o.order_number)}')">Details</button>
                </td>
            </tr>
        `).join("");
    } catch (err) {
        tbody.innerHTML = `<tr><td colspan="7" class="text-center text-danger py-4">${escapeHtml(err.message)}</td></tr>`;
    }
}

window.openOrderModal = async function (orderNumber) {
    const modal = new bootstrap.Modal(document.getElementById("orderDetailModal"));
    document.getElementById("order-modal-title").textContent = `Order ${orderNumber}`;
    const body = document.getElementById("order-modal-body");
    body.innerHTML = `<div class="text-center py-4"><span class="spinner-border"></span></div>`;
    modal.show();

    try {
        const o = await fetchJson(`/api/orders/${encodeURIComponent(orderNumber)}`);
        const itemsHtml = (o.items || []).map((i) => `
            <tr>
                <td>${escapeHtml(i.product_name || "Product #" + i.product_id)}</td>
                <td class="text-center">${i.quantity}</td>
                <td class="text-end">$${Number(i.unit_price || 0).toFixed(2)}</td>
            </tr>
        `).join("");

        body.innerHTML = `
            <div class="row g-3 mb-3">
                <div class="col-md-6">
                    <strong>Customer:</strong> ${escapeHtml(o.customer_name)} (${escapeHtml(o.customer_email)})<br>
                    <strong>Shipping:</strong> ${escapeHtml(o.shipping_address)}
                </div>
                <div class="col-md-6">
                    <strong>Status:</strong> ${statusBadge(o.status)}<br>
                    <strong>Total:</strong> $${Number(o.total_amount || 0).toFixed(2)}<br>
                    <strong>Payment:</strong> ${o.payment ? statusBadge(o.payment.status) + " (" + escapeHtml(o.payment.method) + ")" : "N/A"}<br>
                    <strong>Delivery:</strong> ${o.delivery ? escapeHtml(o.delivery.carrier) + " — " + escapeHtml(o.delivery.tracking_number) + " (" + escapeHtml(o.delivery.status) + ")" : "Not dispatched"}
                </div>
            </div>
            <h6>Items</h6>
            <table class="table table-sm table-bordered">
                <thead><tr><th>Product</th><th class="text-center">Qty</th><th class="text-end">Unit Price</th></tr></thead>
                <tbody>${itemsHtml}</tbody>
            </table>
        `;
    } catch (err) {
        body.innerHTML = `<div class="alert alert-danger">${escapeHtml(err.message)}</div>`;
    }
};

// ── Vendors ──────────────────────────────────────────────────────

async function loadVendors() {
    const tbody = document.getElementById("vendors-table-body");
    try {
        const data = await fetchJson("/api/vendors");
        const vendors = data.vendors || [];
        document.getElementById("vendors-count").textContent = `${vendors.length} vendors`;
        tbody.innerHTML = vendors.map((v) => `
            <tr>
                <td>${v.id}</td>
                <td class="fw-semibold">${escapeHtml(v.name)}</td>
                <td>${escapeHtml(v.company)}</td>
                <td>${escapeHtml(v.email)}</td>
                <td class="text-center">${v.commission_rate}%</td>
                <td class="text-center">${v.is_active ? '<span class="badge bg-success">Active</span>' : '<span class="badge bg-secondary">Inactive</span>'}</td>
                <td class="text-center">${v.product_count ?? "-"}</td>
                <td class="text-end">
                    <button class="btn btn-sm btn-outline-primary" onclick="openVendorModal(${v.id})">Details</button>
                </td>
            </tr>
        `).join("");
    } catch (err) {
        tbody.innerHTML = `<tr><td colspan="8" class="text-center text-danger py-4">${escapeHtml(err.message)}</td></tr>`;
    }
}

window.openVendorModal = async function (vendorId) {
    const modal = new bootstrap.Modal(document.getElementById("vendorDetailModal"));
    const body = document.getElementById("vendor-modal-body");
    body.innerHTML = `<div class="text-center py-4"><span class="spinner-border"></span></div>`;
    modal.show();

    try {
        const v = await fetchJson(`/api/vendors/${vendorId}`);
        document.getElementById("vendor-modal-title").textContent = `${v.company} (${v.name})`;
        const comm = v.commission_summary || {};
        body.innerHTML = `
            <p><strong>Email:</strong> ${escapeHtml(v.email)} | <strong>Phone:</strong> ${escapeHtml(v.phone)}</p>
            <p><strong>Commission Rate:</strong> ${v.commission_rate}% | <strong>Total Sales:</strong> $${Number(comm.total_sales || 0).toFixed(2)} | <strong>Platform Commission:</strong> $${Number(comm.commission_earned || 0).toFixed(2)}</p>
            <p><strong>Products Listed:</strong> ${(v.products || []).length} | <strong>Orders:</strong> ${(v.orders || []).length}</p>
        `;
    } catch (err) {
        body.innerHTML = `<div class="alert alert-danger">${escapeHtml(err.message)}</div>`;
    }
};

// ── Products ─────────────────────────────────────────────────────

async function loadProducts() {
    const category = document.getElementById("product-category-filter")?.value || "";
    const search = document.getElementById("product-search")?.value || "";
    const params = new URLSearchParams();
    if (category) params.set("category", category);
    if (search) params.set("search", search);

    const tbody = document.getElementById("products-table-body");
    try {
        const data = await fetchJson(`/api/products?${params.toString()}`);
        const products = data.products || [];
        document.getElementById("products-count").textContent = `${products.length} products`;
        if (!products.length) {
            tbody.innerHTML = `<tr><td colspan="6" class="text-center py-4 text-muted">No products found.</td></tr>`;
            return;
        }
        tbody.innerHTML = products.map((p) => `
            <tr>
                <td><code>${escapeHtml(p.sku)}</code></td>
                <td class="fw-semibold">${escapeHtml(p.name)}</td>
                <td><span class="badge bg-light text-dark border">${escapeHtml(p.category)}</span></td>
                <td class="text-end">$${Number(p.price || 0).toFixed(2)}</td>
                <td class="text-center">${p.stock}</td>
                <td>${escapeHtml(p.vendor_name || "Vendor #" + p.vendor_id)}</td>
            </tr>
        `).join("");
    } catch (err) {
        tbody.innerHTML = `<tr><td colspan="6" class="text-center text-danger py-4">${escapeHtml(err.message)}</td></tr>`;
    }
}

// ── Meetings ─────────────────────────────────────────────────────

function initMeetings() {
    document.getElementById("cal-prev")?.addEventListener("click", () => {
        window._calStart.setDate(window._calStart.getDate() - 7);
        loadMeetings();
    });
    document.getElementById("cal-next")?.addEventListener("click", () => {
        window._calStart.setDate(window._calStart.getDate() + 7);
        loadMeetings();
    });
    document.getElementById("submit-meeting")?.addEventListener("click", submitMeetingForm);
    window._calStart = getMonday(new Date());
}

async function loadMeetings() {
    try {
        const data = await fetchJson("/api/meetings?limit=50");
        const meetings = data.meetings || [];
        renderUpcomingMeetings(meetings);
        renderWeekCalendar(meetings);
    } catch (err) {
        console.error("Meetings error:", err);
    }
}

function renderUpcomingMeetings(meetings) {
    const container = document.getElementById("upcoming-meetings");
    if (!meetings.length) {
        container.innerHTML = `<p class="text-muted text-center my-4">No upcoming meetings.</p>`;
        return;
    }
    container.innerHTML = meetings.slice(0, 10).map((m) => `
        <div class="border-bottom pb-2 mb-2">
            <div class="d-flex justify-content-between">
                <strong>${escapeHtml(m.title)}</strong>
                ${statusBadge(m.status)}
            </div>
            <div class="small text-muted">
                ${escapeHtml(m.meeting_date)} &middot; ${escapeHtml(m.start_time)}–${escapeHtml(m.end_time)} &middot; ${escapeHtml(m.location || "Virtual")}
            </div>
        </div>
    `).join("");
}

function renderWeekCalendar(meetings) {
    const start = window._calStart || getMonday(new Date());
    const days = [];
    for (let i = 0; i < 7; i++) {
        const d = new Date(start);
        d.setDate(start.getDate() + i);
        days.push(d);
    }
    document.getElementById("calendar-title").textContent =
        `Week of ${fmtDate(days[0])} to ${fmtDate(days[6])}`;

    document.getElementById("calendar-header").innerHTML = days
        .map((d) => `<th>${d.toLocaleDateString(undefined, { weekday: "short", month: "short", day: "numeric" })}</th>`)
        .join("");

    document.getElementById("calendar-body").innerHTML = `<tr>${days
        .map((d) => {
            const iso = fmtDate(d);
            const dayMeetings = meetings.filter((m) => m.meeting_date === iso);
            if (!dayMeetings.length) return `<td class="text-muted small py-3">—</td>`;
            return `<td>${dayMeetings
                .map((m) => `<span class="cal-meeting-pill">${escapeHtml(m.start_time)} ${escapeHtml(m.title)}</span>`)
                .join("")}</td>`;
        })
        .join("")}</tr>`;
}

async function submitMeetingForm() {
    const payload = {
        title: document.getElementById("meeting-title").value.trim(),
        description: document.getElementById("meeting-description").value.trim(),
        organizer: document.getElementById("meeting-organizer").value.trim(),
        attendees: document.getElementById("meeting-attendees").value.trim(),
        meeting_date: document.getElementById("meeting-date").value,
        start_time: document.getElementById("meeting-start").value,
        end_time: document.getElementById("meeting-end").value,
        location: document.getElementById("meeting-location").value.trim() || "Virtual",
    };

    try {
        await fetchJson("/api/meetings", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(payload),
        });
        bootstrap.Modal.getInstance(document.getElementById("scheduleMeetingModal"))?.hide();
        document.getElementById("meeting-form").reset();
        loadMeetings();
    } catch (err) {
        alert("Failed to schedule meeting: " + err.message);
    }
}

// ── Activity Log ─────────────────────────────────────────────────

async function loadActivities() {
    const tbody = document.getElementById("activity-table-body");
    try {
        const data = await fetchJson("/api/activities?limit=50");
        const activities = data.activities || [];
        if (!activities.length) {
            tbody.innerHTML = `<tr><td colspan="5" class="text-center py-4 text-muted">No activities logged yet.</td></tr>`;
            return;
        }
        tbody.innerHTML = activities.map((a) => `
            <tr>
                <td class="small text-muted">${escapeHtml((a.created_at || "").replace("T", " ").slice(0, 19))}</td>
                <td><span class="badge bg-info text-dark">${escapeHtml(a.agent)}</span></td>
                <td><code>${escapeHtml(a.action)}</code></td>
                <td class="small">${escapeHtml(a.user_query || "")}</td>
                <td>${a.success ? '<span class="badge bg-success">Success</span>' : '<span class="badge bg-danger">Failed</span>'}</td>
            </tr>
        `).join("");
    } catch (err) {
        tbody.innerHTML = `<tr><td colspan="5" class="text-center text-danger py-4">${escapeHtml(err.message)}</td></tr>`;
    }
}
