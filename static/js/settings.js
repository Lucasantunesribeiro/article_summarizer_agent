function collectSettingsPayload() {
    return {
        settings: {
            "scraping.timeout": Number(document.getElementById("scrapingTimeout").value),
            "scraping.max_retries": Number(document.getElementById("scrapingRetries").value),
            "scraping.max_content_bytes": Number(document.getElementById("maxContentBytes").value),
            "summarization.default_method": document.getElementById("defaultMethod").value,
            "summarization.default_length": document.getElementById("defaultLength").value,
            "summarization.gemini_model_id": document.getElementById("geminiModelId").value.trim(),
            "output.cache_enabled": document.getElementById("cacheEnabled").value === "true",
            "output.cache_ttl": Number(document.getElementById("cacheTtl").value),
            "rate_limit.submit.max_requests": Number(document.getElementById("submitMaxRequests").value),
            "rate_limit.submit.window_seconds": Number(document.getElementById("submitWindowSeconds").value),
            "rate_limit.auth.max_requests": Number(document.getElementById("authMaxRequests").value),
            "rate_limit.auth.window_seconds": Number(document.getElementById("authWindowSeconds").value),
            "rate_limit.polling.max_requests": Number(document.getElementById("pollingMaxRequests").value),
            "rate_limit.polling.window_seconds": Number(document.getElementById("pollingWindowSeconds").value),
            "rate_limit.admin.max_requests": Number(document.getElementById("adminMaxRequests").value),
            "rate_limit.admin.window_seconds": Number(document.getElementById("adminWindowSeconds").value),
        },
    };
}

function updateAdminStatus(healthPayload, systemPayload, user) {
    const systemStatus = systemPayload?.status || {};
    document.getElementById("settingsUserRole").textContent = user ? `${user.username} / ${user.role}` : "unknown";
    document.getElementById("settingsHealth").textContent = healthPayload?.status || "Unavailable";
    document.getElementById("settingsModel").textContent = systemStatus.config?.gemini_model || "Not reported";
    document.getElementById("settingsCache").textContent = systemStatus.config?.cache_enabled ? "Enabled" : "Disabled";
}

async function refreshAdminStatus() {
    try {
        const [healthResult, statusResult, user] = await Promise.all([
            loadJson("/health"),
            loadJson("/api/status"),
            getCurrentUser(true),
        ]);

        if (statusResult.response.ok && statusResult.data?.success) {
            updateAdminStatus(healthResult.data, statusResult.data, user);
            return;
        }
    } catch (_error) {
        // Ignore and fall through to degraded status state.
    }

    updateAdminStatus({ status: "Unavailable" }, null, null);
}

async function saveSettings() {
    const button = document.getElementById("saveSettingsBtn");
    setButtonBusy(button, true, "Save changes", "Saving...");

    try {
        const { response, data } = await loadJson("/api/settings", {
            authenticated: true,
            method: "PUT",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(collectSettingsPayload()),
        });

        if (!response.ok || !data?.success) {
            throw new Error(data?.error || "Failed to save settings.");
        }

        showAlert("Settings persisted and applied to the runtime.", "success");
        await refreshAdminStatus();
    } catch (error) {
        showAlert(error.message, "danger");
    } finally {
        setButtonBusy(button, false, "Save changes");
    }
}

async function testSettings() {
    const button = document.getElementById("testSettingsBtn");
    setButtonBusy(button, true, "Validate runtime", "Validating...");

    try {
        const { response, data } = await loadJson("/api/settings/test", {
            authenticated: true,
            method: "POST",
            headers: { "Content-Type": "application/json" },
        });

        if (!response.ok || !data?.success) {
            throw new Error(data?.error || "Runtime validation failed.");
        }

        showAlert("Runtime validation completed successfully.", "success");
        updateAdminStatus({ status: "ok" }, data, await getCurrentUser(true));
    } catch (error) {
        showAlert(error.message, "danger");
    } finally {
        setButtonBusy(button, false, "Validate runtime");
    }
}

async function clearCacheFromSettings() {
    const button = document.getElementById("clearCacheBtn");
    setButtonBusy(button, true, "Clear cache", "Clearing...");

    try {
        const confirmed = window.confirm("Clear cached outputs for the pipeline?");
        if (!confirmed) {
            return;
        }

        const { response, data } = await loadJson("/api/limpar-cache", {
            authenticated: true,
            method: "POST",
            headers: { "Content-Type": "application/json" },
        });

        if (!response.ok || !data?.success) {
            throw new Error(data?.error || "Cache clear failed.");
        }

        showAlert("Cache cleared successfully.", "success");
    } catch (error) {
        showAlert(error.message, "danger");
    } finally {
        setButtonBusy(button, false, "Clear cache");
    }
}

async function rotateSecret() {
    const button = document.getElementById("rotateSecretBtn");
    const resultNode = document.getElementById("rotateSecretResult");
    const newSecret = document.getElementById("newSecret").value.trim();
    const gracePeriod = Number(document.getElementById("gracePeriod").value);

    setButtonBusy(button, true, "Rotate JWT secret", "Rotating...");

    try {
        const { response, data } = await loadJson("/api/admin/rotate-secret", {
            authenticated: true,
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                new_secret: newSecret || null,
                grace_period: gracePeriod,
            }),
        });

        if (!response.ok || !data?.success) {
            throw new Error(data?.error || "Secret rotation failed.");
        }

        resultNode.textContent = `active key ${data.active_key_id} / grace ${data.grace_period_seconds}s / valid secrets ${data.active_secrets}`;
        document.getElementById("newSecret").value = "";
        showAlert("JWT signing secret rotated successfully.", "success");
    } catch (error) {
        showAlert(error.message, "danger");
    } finally {
        setButtonBusy(button, false, "Rotate JWT secret");
    }
}

document.addEventListener("DOMContentLoaded", () => {
    document.getElementById("saveSettingsBtn")?.addEventListener("click", saveSettings);
    document.getElementById("testSettingsBtn")?.addEventListener("click", testSettings);
    document.getElementById("clearCacheBtn")?.addEventListener("click", clearCacheFromSettings);
    document.getElementById("rotateSecretBtn")?.addEventListener("click", rotateSecret);
    refreshAdminStatus();
});
