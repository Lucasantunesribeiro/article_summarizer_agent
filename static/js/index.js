/**
 * Index page — summarization form and polling logic.
 */
let currentTaskId = null;
let pollInterval = null;

document.addEventListener('DOMContentLoaded', function() {
    document.getElementById('articleUrl').focus();
    document.getElementById('summarizeForm').addEventListener('submit', handleSubmit);
});

async function handleSubmit(e) {
    e.preventDefault();
    const url = document.getElementById('articleUrl').value.trim();
    const method = document.getElementById('method').value;
    const length = document.getElementById('length').value;

    if (!url) {
        showAlert('<i class="bi bi-exclamation-triangle"></i> Please enter a valid URL.', 'warning');
        return;
    }

    document.getElementById('progressSection').style.display = 'block';
    document.getElementById('resultsSection').style.display = 'none';
    document.getElementById('submitBtn').disabled = true;
    document.getElementById('submitBtn').innerHTML = '<i class="bi bi-hourglass-split"></i> Processing...';

    try {
        const response = await fetch('/api/sumarizar', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ url, method, length })
        });
        const data = await response.json();
        if (data.success) {
            currentTaskId = data.task_id;
            startPolling();
            showAlert('<i class="bi bi-check-circle"></i> Processing started!', 'success');
        } else {
            throw new Error(data.error || 'Unknown error');
        }
    } catch (error) {
        showAlert('<i class="bi bi-exclamation-triangle"></i> Error: ' + error.message, 'danger');
        resetForm();
    }
}

function startPolling() {
    if (pollInterval) clearInterval(pollInterval);
    pollInterval = setInterval(async () => {
        try {
            const response = await fetch('/api/tarefa/' + currentTaskId);
            const data = await response.json();
            if (data.success) {
                const task = data.task;
                updateProgress(task.progress, task.message);
                if (task.status === 'done') {
                    clearInterval(pollInterval);
                    showResults(task.result);
                } else if (task.status === 'failed' || task.status === 'error') {
                    clearInterval(pollInterval);
                    showAlert('<i class="bi bi-exclamation-triangle"></i> Failed: ' + task.message, 'danger');
                    resetForm();
                }
            }
        } catch (error) {
            clearInterval(pollInterval);
            showAlert('<i class="bi bi-exclamation-triangle"></i> Status check error: ' + error.message, 'danger');
            resetForm();
        }
    }, 2000);
}

function updateProgress(progress, message) {
    const bar = document.getElementById('progressBar');
    const msg = document.getElementById('progressMessage');
    bar.style.width = (progress || 0) + '%';
    bar.textContent = (progress || 0) + '%';
    msg.textContent = message || '';
    bar.className = 'progress-bar progress-bar-striped progress-bar-animated';
    if (progress >= 100) bar.classList.add('bg-success');
    else if (progress >= 50) bar.classList.add('bg-info');
}

function showResults(result) {
    document.getElementById('progressSection').style.display = 'none';
    document.getElementById('resultsSection').style.display = 'block';
    document.getElementById('summaryText').textContent = result.summary || '';
    const stats = result.statistics || {};
    document.getElementById('originalWords').textContent = formatNumber(stats.words_original || 0);
    document.getElementById('summaryWords').textContent = formatNumber(stats.words_summary || 0);
    document.getElementById('compressionRatio').textContent = ((stats.compression_ratio || 0) * 100).toFixed(1) + '%';
    document.getElementById('executionTime').textContent = formatTime(result.execution_time || 0);
    setupDownloadButtons(result.files_created || {});
    document.getElementById('resultsSection').scrollIntoView({ behavior: 'smooth' });
}

function setupDownloadButtons(files) {
    ['txt', 'md', 'json'].forEach(fmt => {
        const btn = document.getElementById('download' + fmt.charAt(0).toUpperCase() + fmt.slice(1));
        if (btn) {
            btn.disabled = !files[fmt];
            btn.onclick = files[fmt] ? () => downloadFile(fmt) : null;
        }
    });
}

async function downloadFile(format) {
    try {
        const response = await fetch('/api/download/' + currentTaskId + '/' + format);
        if (response.ok) {
            const blob = await response.blob();
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = 'summary_' + currentTaskId + '.' + format;
            document.body.appendChild(a);
            a.click();
            window.URL.revokeObjectURL(url);
            document.body.removeChild(a);
            showAlert('<i class="bi bi-download"></i> Download started!', 'success');
        } else {
            throw new Error('Download failed');
        }
    } catch (error) {
        showAlert('<i class="bi bi-exclamation-triangle"></i> Download error: ' + error.message, 'danger');
    }
}

function resetForm() {
    document.getElementById('submitBtn').disabled = false;
    document.getElementById('submitBtn').innerHTML = '<i class="bi bi-play-circle"></i> Gerar Resumo';
    document.getElementById('progressSection').style.display = 'none';
}

function startNewSummarization() {
    document.getElementById('resultsSection').style.display = 'none';
    document.getElementById('progressSection').style.display = 'none';
    resetForm();
    document.getElementById('articleUrl').value = '';
    document.getElementById('method').value = 'extractive';
    document.getElementById('length').value = 'medium';
    document.getElementById('articleUrl').focus();
    window.scrollTo({ top: 0, behavior: 'smooth' });
}
