let currentTaskId = null;
let currentTaskUrl = null;
let pollInterval = null;

function showSection(sectionId, visible) {
    const element = document.getElementById(sectionId);
    if (!element) {
        return;
    }
    element.classList.toggle("d-none", !visible);
}

function updateStatusCards(healthPayload, systemPayload) {
    const health = document.getElementById("publicStatus");
    const statusPill = document.getElementById("homeStatusPill");
    const model = document.getElementById("activeModel");
    const cache = document.getElementById("cacheStrategy");
    const method = document.getElementById("activeMethod");
    const systemStatus = systemPayload?.status || {};
    const healthStatus = healthPayload?.status || "Unavailable";

    if (health) {
        health.textContent = healthStatus;
    }
    if (statusPill) {
        statusPill.textContent = healthStatus === "ok" ? "API online" : "API degraded";
        statusPill.classList.toggle("status-pill--danger", healthStatus !== "ok");
    }
    if (model) {
        model.textContent = systemStatus.config?.gemini_model || "Not reported";
    }
    if (cache) {
        cache.textContent = systemStatus.config?.cache_enabled ? "Enabled" : "Disabled";
    }
    if (method && systemStatus.config?.summarization_method) {
        method.textContent = systemStatus.config.summarization_method;
    }
}

async function loadPublicStatus() {
    try {
        const [healthResult, statusResult] = await Promise.all([
            loadJson("/health"),
            loadJson("/api/status"),
        ]);

        if (statusResult.response.ok && statusResult.data?.success) {
            updateStatusCards(healthResult.data, statusResult.data);
            return;
        }
    } catch (_error) {
        // Ignore and fall through to unavailable status.
    }

    updateStatusCards({ status: "Unavailable" }, null);
}

function updateProgress(progress, message, status) {
    const progressBar = document.getElementById("progressBar");
    const progressMessage = document.getElementById("progressMessage");
    const progressStage = document.getElementById("progressStage");
    const progressMeta = document.getElementById("progressMeta");

    const safeProgress = Math.max(0, Math.min(100, Number(progress || 0)));
    if (progressBar) {
        progressBar.style.width = `${safeProgress}%`;
        progressBar.parentElement?.setAttribute("aria-valuenow", String(safeProgress));
    }
    if (progressMessage) {
        progressMessage.textContent = message || "Processing task.";
    }
    if (progressStage) {
        progressStage.textContent = safeProgress >= 100 ? "Task completed" : "Task in progress";
    }
    if (progressMeta) {
        progressMeta.textContent = `${status || "queued"} / ${safeProgress}%`;
    }
}

function setupDownloadButtons(filesCreated) {
    ["txt", "md", "json"].forEach((format) => {
        const button = document.getElementById(`download${format.charAt(0).toUpperCase()}${format.slice(1)}`);
        if (!button) {
            return;
        }
        const hasFile = Boolean(filesCreated?.[format]);
        button.disabled = !hasFile;
        button.onclick = hasFile ? () => downloadFile(format) : null;
    });
}

function populateResult(task) {
    const result = task.result || {};
    const stats = result.statistics || {};

    document.getElementById("resultSummaryText").textContent = result.summary || "";
    document.getElementById("resultMethodUsed").textContent = result.method_used || task.method || "unknown";
    document.getElementById("originalWords").textContent = formatNumber(stats.words_original || 0);
    document.getElementById("summaryWords").textContent = formatNumber(stats.words_summary || 0);
    document.getElementById("compressionRatio").textContent = `${((stats.compression_ratio || 0) * 100).toFixed(1)}%`;
    document.getElementById("executionTime").textContent = formatTime(result.execution_time || 0);
    document.getElementById("taskReference").textContent = task.id || currentTaskId || "n/a";
    document.getElementById("articleOrigin").textContent = task.url || currentTaskUrl || "n/a";
    setupDownloadButtons(result.files_created || {});

    showSection("progressSection", false);
    showSection("resultsSection", true);
    document.getElementById("resultsSection")?.scrollIntoView({ behavior: "smooth", block: "start" });
}

function resetForm() {
    const submitButton = document.getElementById("submitBtn");
    setButtonBusy(submitButton, false, "Start summarization");
    showSection("progressSection", false);
}

async function downloadFile(format) {
    if (!currentTaskId) {
        return;
    }

    try {
        const response = await fetch(`/api/download/${currentTaskId}/${format}`);
        if (!response.ok) {
            throw new Error("Download failed.");
        }

        const blob = await response.blob();
        const objectUrl = window.URL.createObjectURL(blob);
        const anchor = document.createElement("a");
        anchor.href = objectUrl;
        anchor.download = `summary_${currentTaskId}.${format}`;
        document.body.appendChild(anchor);
        anchor.click();
        document.body.removeChild(anchor);
        window.URL.revokeObjectURL(objectUrl);
        showAlert(`Download started for ${format.toUpperCase()}.`, "success");
    } catch (error) {
        showAlert(error.message, "danger");
    }
}

function startPolling() {
    window.clearInterval(pollInterval);
    pollInterval = window.setInterval(async () => {
        try {
            const { response, data } = await loadJson(`/api/tarefa/${currentTaskId}`);
            if (!response.ok || !data?.success) {
                throw new Error(data?.error || "Task lookup failed.");
            }

            const task = data.task;
            updateProgress(task.progress, task.message, task.status);

            if (task.status === "done") {
                window.clearInterval(pollInterval);
                setButtonBusy(document.getElementById("submitBtn"), false, "Start summarization");
                populateResult(task);
            }

            if (task.status === "failed" || task.status === "error") {
                window.clearInterval(pollInterval);
                resetForm();
                showAlert(task.error || task.message || "Task failed.", "danger");
            }
        } catch (error) {
            window.clearInterval(pollInterval);
            resetForm();
            showAlert(error.message, "danger");
        }
    }, 2000);
}

async function handleSubmit(event) {
    event.preventDefault();

    const urlField = document.getElementById("articleUrl");
    const methodField = document.getElementById("method");
    const lengthField = document.getElementById("length");
    const submitButton = document.getElementById("submitBtn");

    const url = urlField.value.trim();
    const method = methodField.value;
    const length = lengthField.value;

    if (!url) {
        showAlert("Provide a valid public URL.", "warning");
        return;
    }

    currentTaskUrl = url;
    showSection("resultsSection", false);
    showSection("progressSection", true);
    updateProgress(5, "Submitting task to the API.", "queued");
    setButtonBusy(submitButton, true, "Start summarization", "Submitting...");

    try {
        const { response, data } = await loadJson("/api/sumarizar", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ url, method, length }),
        });

        if (!response.ok || !data?.success) {
            throw new Error(data?.error || "Task submission failed.");
        }

        currentTaskId = data.task_id;
        document.getElementById("taskReference").textContent = currentTaskId;
        updateProgress(10, "Task accepted and queued for processing.", "queued");
        startPolling();
        showAlert("Task submitted successfully.", "success");
    } catch (error) {
        resetForm();
        showAlert(error.message, "danger");
    }
}

function startNewSummarization() {
    window.clearInterval(pollInterval);
    currentTaskId = null;
    currentTaskUrl = null;
    document.getElementById("summarizeForm")?.reset();
    document.getElementById("articleUrl").focus();
    resetForm();
    showSection("resultsSection", false);
    window.scrollTo({ top: 0, behavior: "smooth" });
}

document.addEventListener("DOMContentLoaded", () => {
    document.getElementById("articleUrl")?.focus();
    document.getElementById("summarizeForm")?.addEventListener("submit", handleSubmit);
    loadPublicStatus();
});

window.startNewSummarization = startNewSummarization;
