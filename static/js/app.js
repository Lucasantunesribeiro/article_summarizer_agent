function showAlert(message, type = "info") {
    const alertContainer = document.getElementById("alert-container");
    if (!alertContainer) {
        return;
    }

    const alertId = `alert-${Date.now()}`;
    alertContainer.innerHTML = "";

    const alertElement = document.createElement("div");
    alertElement.id = alertId;
    alertElement.className = `app-alert app-alert--${type}`;
    alertElement.setAttribute("role", "alert");

    const content = document.createElement("div");
    content.className = "app-alert__content";
    content.textContent = message;

    const closeButton = document.createElement("button");
    closeButton.type = "button";
    closeButton.className = "app-alert__close";
    closeButton.setAttribute("aria-label", "Fechar alerta");
    closeButton.textContent = "x";
    closeButton?.addEventListener("click", () => alertElement.remove());

    alertElement.appendChild(content);
    alertElement.appendChild(closeButton);
    alertContainer.appendChild(alertElement);

    window.setTimeout(() => {
        alertElement?.remove();
    }, 5000);
}

function formatTime(seconds) {
    if (seconds < 60) {
        return `${seconds.toFixed(1)}s`;
    }
    if (seconds < 3600) {
        return `${Math.floor(seconds / 60)}m ${Math.floor(seconds % 60)}s`;
    }
    return `${Math.floor(seconds / 3600)}h ${Math.floor((seconds % 3600) / 60)}m`;
}

function formatNumber(num) {
    return new Intl.NumberFormat("pt-BR").format(num);
}

function setButtonBusy(button, busy, idleLabel, busyLabel = "Working...") {
    if (!button) {
        return;
    }
    button.disabled = busy;
    button.textContent = busy ? busyLabel : idleLabel;
}

async function loadJson(url, options = {}) {
    const response = options.authenticated ? await authFetch(url, options) : await fetch(url, options);
    let data = null;
    try {
        data = await response.json();
    } catch (_error) {
        data = null;
    }
    return { response, data };
}

async function clearCache() {
    const confirmed = window.confirm("Clear cached outputs and scraper cache?");
    if (!confirmed) {
        return;
    }

    try {
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
    }
}

window.showAlert = showAlert;
window.formatTime = formatTime;
window.formatNumber = formatNumber;
window.setButtonBusy = setButtonBusy;
window.loadJson = loadJson;
window.clearCache = clearCache;
