// MeliSim — API client.
// Plain ES2017 (no JSX). Loaded as a regular <script> before any *.jsx file.
//
// Base URL for `/api/v1/*`:
// - Default: '' (relative) so requests hit the same host:port as the page — when
//   served by Docker web-ui, nginx proxies `/api/` → api-gateway (no CORS, one
//   port for mobile).
// - Override: set `window.MELISIM_API` before this script (e.g. dev server on :9000
//   → `http://localhost:8000`).
// - `file://` pages fall back to `http://localhost:8000`.

(function () {
  function resolveApiBase() {
    if (typeof window === 'undefined') return 'http://localhost:8000';
    if (window.MELISIM_API) return window.MELISIM_API;
    const p = window.location.protocol;
    if (p === 'file:' || p === 'blob:' || !p) return 'http://localhost:8000';
    return '';
  }
  const API = resolveApiBase();

  const TOKEN_KEY = 'melisim.jwt';
  const USER_KEY  = 'melisim.user';

  function getToken() { return localStorage.getItem(TOKEN_KEY); }
  function getUser() {
    try {
      const u = JSON.parse(localStorage.getItem(USER_KEY) || 'null');
      if (!u) return null;
      if (!u.userType && u.user_type) return { ...u, userType: u.user_type };
      return u;
    } catch {
      return null;
    }
  }
  function setSession(token, user) {
    localStorage.setItem(TOKEN_KEY, token);
    if (user && !user.userType && user.user_type) user = { ...user, userType: user.user_type };
    localStorage.setItem(USER_KEY, JSON.stringify(user));
  }
  function clearSession() {
    localStorage.removeItem(TOKEN_KEY);
    localStorage.removeItem(USER_KEY);
  }
  function isLoggedIn() { return !!getToken(); }

  function authHeader() {
    const t = getToken();
    return t ? { 'Authorization': `Bearer ${t}` } : {};
  }

  function makeRequestId() {
    if (window.crypto && window.crypto.randomUUID) return window.crypto.randomUUID().replace(/-/g, '');
    return Math.random().toString(16).slice(2) + Date.now().toString(16);
  }

  async function http(method, path, { body, headers, auth = true, idempotencyKey } = {}) {
    const url = `${API}${path}`;
    const h = {
      'Accept': 'application/json',
      'X-Request-ID': makeRequestId(),
      ...(body ? { 'Content-Type': 'application/json' } : {}),
      ...(auth ? authHeader() : {}),
      ...(idempotencyKey ? { 'Idempotency-Key': idempotencyKey } : {}),
      ...(headers || {}),
    };
    const res = await fetch(url, { method, headers: h, body: body ? JSON.stringify(body) : undefined });
    if (res.status === 401 && auth) {
      // Session expired or invalid — drop everything and ask for fresh login.
      clearSession();
      if (!location.pathname.endsWith('01-login.html')) location.href = '01-login.html?expired=1';
      const unauth = new Error('unauthorized');
      unauth.status = 401;
      throw unauth;
    }
    const text = await res.text();
    const data = text ? safeJson(text) : null;
    if (!res.ok) {
      const err = new Error((data && (data.message || data.detail || data.error)) || `${res.status} ${res.statusText}`);
      err.status = res.status;
      err.body = data;
      throw err;
    }
    return data;
  }

  function safeJson(s) { try { return JSON.parse(s); } catch { return s; } }

  const api = {
    /* ------------ Session ------------ */
    isLoggedIn, getUser, getToken, clearSession,

    async register({ name, email, password, userType }) {
      // users-service expects { name, email, password, userType }
      const r = await http('POST', '/api/v1/auth/register',
        { body: { name, email, password, userType }, auth: false });
      return r;
    },

    async login({ email, password }) {
      const r = await http('POST', '/api/v1/auth/login',
        { body: { email, password }, auth: false });
      const token = r.accessToken ?? r.access_token;
      let user = r.user;
      if (user && !user.userType && user.user_type) user = { ...user, userType: user.user_type };
      setSession(token, user);
      return r;
    },

    logout() {
      clearSession();
      location.href = '01-login.html';
    },

    /* ------------ Users ------------ */
    getUserById: (id)        => http('GET',  `/api/v1/users/${id}`),
    updateUser:  (id, patch) => http('PUT',  `/api/v1/users/${id}`, { body: patch }),

    /* ------------ Products ------------ */
    listProducts: ({ page = 1, size = 20 } = {}) =>
      http('GET', `/api/v1/products?page=${page}&size=${size}`, { auth: false }),

    getProduct:   (id) => http('GET',  `/api/v1/products/${id}`, { auth: false }),
    createProduct: (p) => http('POST', `/api/v1/products`, { body: p }),

    /* ------------ Search ------------ */
    search: ({ q = '', category, minPrice, maxPrice, size = 20 } = {}) => {
      const qs = new URLSearchParams();
      if (q) qs.set('q', q);
      if (category) qs.set('category', category);
      if (minPrice != null) qs.set('min_price', minPrice);
      if (maxPrice != null) qs.set('max_price', maxPrice);
      qs.set('size', size);
      return http('GET', `/api/v1/products/search?${qs.toString()}`, { auth: false });
    },

    /* ------------ Orders ------------ */
    createOrder: ({ buyerId, productId, quantity }) =>
      http('POST', '/api/v1/orders', { body: { buyerId, productId, quantity } }),

    getOrder:    (id)     => http('GET', `/api/v1/orders/${id}`),
    listOrdersByUser: (userId) => http('GET', `/api/v1/orders/user/${userId}`),

    /* ------------ Payments ------------ */
    createPayment: ({ orderId, amount, method, idempotencyKey }) =>
      http('POST', '/api/v1/payments', {
        body: { order_id: orderId, amount, method },
        idempotencyKey: idempotencyKey || makeRequestId(),
      }),

    /* ------------ Notifications ------------ */
    listNotifications: (userId) => http('GET', `/api/v1/notifications/user/${userId}`),

    /* ------------ Service health (admin) ------------ */
    // Aggregated health from the gateway. Browser → /api/v1/admin/services-health,
    // gateway pings each service from the docker network (no CORS issues).
    getAllServicesHealth: () => http('GET', '/api/v1/admin/services-health'),

    /** Prometheus + outbox aggregates for admin dashboard KPI row. */
    getAdminDashboardKpis: () => http('GET', '/api/v1/admin/dashboard-kpis'),

    /** Per-service RPS + p95 (Prometheus `job` = service name). */
    getAdminServiceMetrics: () => http('GET', '/api/v1/admin/service-metrics'),

    getOutboxSummary: () => http('GET', '/api/v1/admin/outbox/summary'),

    getDlqTopics: () => http('GET', '/api/v1/admin/dlq/topics'),

    // Direct ping kept as fallback. CORS will block JVM/Go services; use
    // getAllServicesHealth in production-style admin UIs.
    async ping(serviceUrl) {
      const start = performance.now();
      try {
        const res = await fetch(serviceUrl, { method: 'GET', mode: 'cors' });
        return { up: res.ok, status: res.status, elapsedMs: Math.round(performance.now() - start) };
      } catch (e) {
        return { up: false, status: 0, elapsedMs: Math.round(performance.now() - start), error: String(e) };
      }
    },
  };

  /* ------------ Cart (browser-local — there is no cart-service) ------------ */
  const CART_KEY = 'melisim.cart';
  api.cart = {
    items() { try { return JSON.parse(localStorage.getItem(CART_KEY) || '[]'); } catch { return []; } },
    count() { return api.cart.items().reduce((s, it) => s + it.qty, 0); },
    total() { return api.cart.items().reduce((s, it) => s + it.qty * it.price, 0); },
    add(product, qty = 1) {
      const items = api.cart.items();
      const idx = items.findIndex(it => it.id === product.id);
      if (idx >= 0) items[idx].qty += qty;
      else items.push({ id: product.id, title: product.title, price: Number(product.price), qty });
      localStorage.setItem(CART_KEY, JSON.stringify(items));
      window.dispatchEvent(new CustomEvent('melisim:cart-changed'));
    },
    setQty(productId, qty) {
      let items = api.cart.items();
      items = items
        .map(it => it.id === productId ? { ...it, qty: Math.max(0, qty) } : it)
        .filter(it => it.qty > 0);
      localStorage.setItem(CART_KEY, JSON.stringify(items));
      window.dispatchEvent(new CustomEvent('melisim:cart-changed'));
    },
    remove(productId) { api.cart.setQty(productId, 0); },
    clear() {
      localStorage.removeItem(CART_KEY);
      window.dispatchEvent(new CustomEvent('melisim:cart-changed'));
    },
  };

  /* ------------ Auth gate helper for protected pages ------------ */
  api.requireAuth = function (loginUrl = '01-login.html') {
    if (!isLoggedIn()) {
      const here = location.pathname.split('/').pop() || '';
      location.href = `${loginUrl}?next=${encodeURIComponent(here)}`;
      return false;
    }
    return true;
  };

  /** Only ADMIN users (operator UI). Others are redirected to the marketplace home. */
  api.requireAdmin = function (loginUrl = '01-login.html', buyerHome = '10-buyer-home.html') {
    if (!isLoggedIn()) {
      const here = location.pathname.split('/').pop() || '';
      location.href = `${loginUrl}?next=${encodeURIComponent(here)}`;
      return false;
    }
    const u = getUser();
    if (u?.userType !== 'ADMIN') {
      location.href = buyerHome;
      return false;
    }
    return true;
  };

  /** Base URL used for `/api/v1/*` (login, admin health, etc.). */
  api.gatewayUrl = API;

  window.MeliSim = api;
})();
