/**
 * static/js/app.js
 *
 * Shared frontend helpers used by every page:
 *  - Token storage (sessionStorage) and retrieval
 *  - A fetch() wrapper (EMS.api) that automatically attaches the
 *    "Authorization: Bearer <token>" header for protected API calls
 *  - A small Bootstrap alert helper
 *  - Login-state-aware navbar rendering (Logout button) + a requireAuth()
 *    guard used on pages that need a logged-in user
 */

const EMS = (function () {
    const TOKEN_KEY = "ems_access_token";

    function getToken() {
        return sessionStorage.getItem(TOKEN_KEY);
    }

    function setToken(token) {
        sessionStorage.setItem(TOKEN_KEY, token);
    }

    function clearToken() {
        sessionStorage.removeItem(TOKEN_KEY);
    }

    function isLoggedIn() {
        return !!getToken();
    }

    /**
     * requireAuth(): call at the top of any page that requires login.
     * Redirects to /login if no token is present.
     */
    function requireAuth() {
        if (!isLoggedIn()) {
            window.location.href = "/login";
        }
    }

    function logout() {
        clearToken();
        window.location.href = "/login";
    }

    function showAlert(message, type = "info") {
        const area = document.getElementById("alert-area");
        if (!area) return;
        const div = document.createElement("div");
        div.className = `alert alert-${type} alert-dismissible fade show`;
        div.role = "alert";
        div.innerHTML = `${message}<button type="button" class="btn-close" data-bs-dismiss="alert"></button>`;
        area.appendChild(div);
        setTimeout(() => div.remove(), 5000);
    }

    /**
     * api(path, options): a thin wrapper around fetch() for calling the
     * JSON API. Automatically:
     *   - Prefixes nothing (paths are already absolute, e.g. "/employees")
     *   - Sends "Content-Type: application/json" + JSON-encodes `body`
     *   - Attaches the stored JWT as "Authorization: Bearer <token>" unless
     *     `auth: false` is passed (used for /auth/signup)
     *   - Throws an Error with the API's `detail` message on non-2xx responses
     *   - On 401 Unauthorized, clears the token and redirects to /login
     */
    async function api(path, { method = "GET", body = null, auth = true } = {}) {
        const headers = { "Content-Type": "application/json" };
        if (auth) {
            const token = getToken();
            if (token) headers["Authorization"] = `Bearer ${token}`;
        }

        const res = await fetch(path, {
            method,
            headers,
            body: body ? JSON.stringify(body) : undefined,
        });

        if (res.status === 401) {
            clearToken();
            window.location.href = "/login";
            throw new Error("Session expired. Please log in again.");
        }

        if (res.status === 204) {
            return null;
        }

        const data = await res.json().catch(() => ({}));

        if (!res.ok) {
            const message =
                typeof data.detail === "string"
                    ? data.detail
                    : Array.isArray(data.errors)
                    ? data.errors.map((e) => e.msg).join(", ")
                    : "Request failed";
            throw new Error(message);
        }

        return data;
    }

    function renderNavAuthArea() {
        const el = document.getElementById("nav-auth-area");
        if (!el) return;
        if (isLoggedIn()) {
            el.innerHTML = `<button class="btn btn-outline-light btn-sm" onclick="EMS.logout()">Logout</button>`;
        } else {
            el.innerHTML = `<a class="btn btn-outline-light btn-sm" href="/login">Login</a>`;
        }
    }

    document.addEventListener("DOMContentLoaded", renderNavAuthArea);

    return { getToken, setToken, clearToken, isLoggedIn, requireAuth, logout, showAlert, api };
})();
