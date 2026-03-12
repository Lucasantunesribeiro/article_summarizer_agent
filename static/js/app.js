/**
 * Shared utility functions for Article Summarizer Agent.
 */

function showAlert(message, type = 'info') {
    const alertContainer = document.getElementById('alert-container');
    const alertId = 'alert-' + Date.now();
    const alertHTML = `
        <div id="${alertId}" class="alert alert-${type} alert-dismissible fade show" role="alert">
            ${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        </div>`;
    alertContainer.innerHTML = alertHTML;
    setTimeout(() => {
        const alert = document.getElementById(alertId);
        if (alert) {
            new bootstrap.Alert(alert).close();
        }
    }, 5000);
}

async function clearCache() {
    try {
        const response = await authFetch('/api/limpar-cache', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
        });
        const data = await response.json();
        if (data.success) {
            showAlert('<i class="bi bi-check-circle"></i> Cache cleared!', 'success');
        } else {
            showAlert('<i class="bi bi-exclamation-triangle"></i> Error: ' + data.error, 'danger');
        }
    } catch (error) {
        showAlert('<i class="bi bi-exclamation-triangle"></i> Error: ' + error.message, 'danger');
    }
}

function formatTime(seconds) {
    if (seconds < 60) return seconds.toFixed(1) + 's';
    if (seconds < 3600) return Math.floor(seconds / 60) + 'm ' + Math.floor(seconds % 60) + 's';
    return Math.floor(seconds / 3600) + 'h ' + Math.floor((seconds % 3600) / 60) + 'm';
}

function formatNumber(num) {
    return new Intl.NumberFormat('pt-BR').format(num);
}
