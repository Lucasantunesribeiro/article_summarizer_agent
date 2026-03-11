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

/**
 * Authenticated fetch — adds Authorization: Bearer header when a token exists.
 */
async function authFetch(url, options = {}) {
    const token = getAccessToken();
    const headers = { ...(options.headers || {}) };
    if (token) {
        headers['Authorization'] = 'Bearer ' + token;
    }
    return fetch(url, { ...options, headers });
}

/**
 * Update the navbar login/logout link based on current auth state.
 */
function updateNavAuth() {
    const token = getAccessToken();
    const loginLink = document.getElementById('nav-login-link');
    const logoutLink = document.getElementById('nav-logout-link');
    if (!loginLink || !logoutLink) return;
    if (token) {
        loginLink.classList.add('d-none');
        logoutLink.classList.remove('d-none');
    } else {
        loginLink.classList.remove('d-none');
        logoutLink.classList.add('d-none');
    }
}

document.addEventListener('DOMContentLoaded', updateNavAuth);
