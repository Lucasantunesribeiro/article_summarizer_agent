function applyHistoryFilter() {
    const filter = document.getElementById("historyStatusFilter");
    const cards = Array.from(document.querySelectorAll(".history-card"));
    const selectedStatus = filter?.value || "all";

    cards.forEach((card) => {
        const matches = selectedStatus === "all" || card.dataset.status === selectedStatus;
        card.classList.toggle("d-none", !matches);
    });
}

async function loadHistoryStats() {
    try {
        const { response, data } = await loadJson("/api/estatisticas", { authenticated: true });
        if (!response.ok || !data?.success) {
            return;
        }

        document.getElementById("historyTotal").textContent = formatNumber(data.stats.total || 0);
        document.getElementById("historyDone").textContent = formatNumber(data.stats.done || 0);
        document.getElementById("historyFailed").textContent = formatNumber(data.stats.failed || 0);
        document.getElementById("historyRunning").textContent = formatNumber(data.stats.running || 0);
    } catch (_error) {
        // Keep server-rendered totals if stats cannot be loaded.
    }
}

document.addEventListener("DOMContentLoaded", () => {
    document.getElementById("historyStatusFilter")?.addEventListener("change", applyHistoryFilter);
    loadHistoryStats();
});
