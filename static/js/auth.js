const ACCESS_COOKIE_HINTS = [
    "csrf_access_token",
    "access_token_cookie",
    "csrf_refresh_token",
    "refresh_token_cookie",
];

function getCookie(name) {
    const prefix = `${name}=`;
    return document.cookie
        .split(";")
        .map((part) => part.trim())
        .find((part) => part.startsWith(prefix))
        ?.slice(prefix.length) || null;
}

function hasAuthCookie() {
    return ACCESS_COOKIE_HINTS.some((cookieName) => Boolean(getCookie(cookieName)));
}

async function authLogin(username, password) {
    try {
        const response = await fetch("/api/auth/login", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            credentials: "same-origin",
            body: JSON.stringify({ username, password }),
        });
        return await response.json();
    } catch (error) {
        return { success: false, error: error.message };
    }
}

function authLogout() {
    sessionStorage.removeItem("access_token");
    sessionStorage.removeItem("refresh_token");
}

async function authFetch(url, options = {}) {
    const headers = { ...(options.headers || {}) };
    const csrfToken = getCookie("csrf_access_token") || getCookie("csrf_refresh_token");
    if (csrfToken) {
        headers["X-CSRF-TOKEN"] = csrfToken;
    }
    return fetch(url, {
        credentials: "same-origin",
        ...options,
        headers,
    });
}

async function getCurrentUser(force = false) {
    if (!force && !hasAuthCookie()) {
        return null;
    }

    try {
        const response = await authFetch("/api/auth/me");
        if (!response.ok) {
            return null;
        }
        const data = await response.json();
        return data.success ? data.user : null;
    } catch (_error) {
        return null;
    }
}

async function updateNavAuth() {
    const user = await getCurrentUser(false);
    const loginLink = document.getElementById("nav-login-link");
    const logoutLink = document.getElementById("nav-logout-link");
    const clearCacheButton = document.getElementById("nav-clear-cache-button");
    const userPill = document.getElementById("nav-user-pill");
    const userText = document.getElementById("nav-user-text");

    if (!loginLink || !logoutLink) {
        return;
    }

    if (user) {
        loginLink.classList.add("d-none");
        logoutLink.classList.remove("d-none");
        clearCacheButton?.classList.remove("d-none");
        userPill?.classList.remove("d-none");
        if (userText) {
            userText.textContent = `${user.username} / ${user.role}`;
        }
        document.body.dataset.authenticated = "true";
    } else {
        loginLink.classList.remove("d-none");
        logoutLink.classList.add("d-none");
        clearCacheButton?.classList.add("d-none");
        userPill?.classList.add("d-none");
        if (userText) {
            userText.textContent = "guest";
        }
        document.body.dataset.authenticated = "false";
    }
}

document.addEventListener("DOMContentLoaded", updateNavAuth);

document.addEventListener("DOMContentLoaded", () => {
    const logoutLink = document.getElementById("nav-logout-link");
    if (!logoutLink) {
        return;
    }

    logoutLink.addEventListener("click", async (event) => {
        event.preventDefault();
        await authFetch("/api/auth/logout", { method: "POST" });
        authLogout();
        window.location.href = "/";
    });
});

window.authFetch = authFetch;
window.authLogin = authLogin;
window.authLogout = authLogout;
window.getCurrentUser = getCurrentUser;
window.updateNavAuth = updateNavAuth;
