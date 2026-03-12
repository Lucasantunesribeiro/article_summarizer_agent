/**
 * Auth utilities — token storage and authenticated fetch helpers.
 *
 * Tokens are stored in sessionStorage (cleared when the tab closes).
 * The access token is sent as an Authorization: Bearer header on API calls.
 */

const TOKEN_KEY = 'access_token';
const REFRESH_KEY = 'refresh_token';

/**
 * Login with username/password. Stores tokens in sessionStorage.
 * Returns {success, error?}.
 */
async function authLogin(username, password) {
    try {
        const resp = await fetch('/api/auth/login', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ username, password }),
        });
        const data = await resp.json();
        if (data.success) {
            sessionStorage.setItem(TOKEN_KEY, data.access_token);
            if (data.refresh_token) {
                sessionStorage.setItem(REFRESH_KEY, data.refresh_token);
            }
        }
        return data;
    } catch (err) {
        return { success: false, error: err.message };
    }
}

/**
 * Logout — clear stored tokens.
 */
function authLogout() {
    sessionStorage.removeItem(TOKEN_KEY);
    sessionStorage.removeItem(REFRESH_KEY);
}

/**
 * Return the stored access token, or null if not logged in.
 */
function getAccessToken() {
    return sessionStorage.getItem(TOKEN_KEY);
}

function getCookie(name) {
    const prefix = name + "=";
    return document.cookie
        .split(";")
        .map(part => part.trim())
        .find(part => part.startsWith(prefix))
        ?.slice(prefix.length) || null;
}

/**
 * Authenticated fetch — adds Authorization: Bearer header when a token exists.
 */
async function authFetch(url, options = {}) {
    const token = getAccessToken();
    const headers = { ...(options.headers || {}) };
    if (token) {
        headers['Authorization'] = 'Bearer ' + token;
    }
    const csrfToken = getCookie('csrf_access_token') || getCookie('csrf_refresh_token');
    if (csrfToken) {
        headers['X-CSRF-TOKEN'] = csrfToken;
    }
    return fetch(url, { ...options, headers });
}

async function getCurrentUser() {
    try {
        const response = await authFetch('/api/auth/me');
        if (!response.ok) {
            return null;
        }
        const data = await response.json();
        return data.success ? data.user : null;
    } catch (_error) {
        return null;
    }
}

/**
 * Update the navbar login/logout link based on current auth state.
 */
async function updateNavAuth() {
    const user = await getCurrentUser();
    const loginLink = document.getElementById('nav-login-link');
    const logoutLink = document.getElementById('nav-logout-link');
    const clearCacheButton = document.getElementById('nav-clear-cache-button');
    if (!loginLink || !logoutLink) return;
    if (user) {
        loginLink.classList.add('d-none');
        logoutLink.classList.remove('d-none');
        if (clearCacheButton) {
            clearCacheButton.classList.remove('d-none');
        }
    } else {
        loginLink.classList.remove('d-none');
        logoutLink.classList.add('d-none');
        if (clearCacheButton) {
            clearCacheButton.classList.add('d-none');
        }
    }
}

document.addEventListener('DOMContentLoaded', updateNavAuth);

document.addEventListener('DOMContentLoaded', () => {
    const logoutLink = document.getElementById('nav-logout-link');
    if (!logoutLink) return;
    logoutLink.addEventListener('click', async (event) => {
        event.preventDefault();
        await authFetch('/api/auth/logout', { method: 'POST' });
        authLogout();
        window.location.href = '/';
    });
});
