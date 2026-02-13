/**
 * generate.js — Visual Batch Planner with Interactive Calendar
 *
 * Full month calendar where you click dates to select ranges,
 * then assign themes. Batches run sequentially on execute.
 */

const BATCH_COLORS = [
    '#58a6ff', '#3fb950', '#d29922', '#f85149',
    '#bc8cff', '#79c0ff', '#56d364', '#e3b341',
];
const DIFFICULTY_CYCLE = ['Easy', 'Easy', 'Medium', 'Medium', 'Hard', 'Hard', 'Medium'];

const DATA = JSON.parse(document.getElementById('generateDataJSON').textContent);
const scheduledSet = new Set(DATA.scheduledDates);

let batches = [];
let selectionStart = null; // date string of first click
let selectionEnd = null;   // date string of last click

// ─────────────────────────────────────────────
// Helpers
// ─────────────────────────────────────────────

function formatDate(d) {
    const y = d.getFullYear();
    const m = String(d.getMonth() + 1).padStart(2, '0');
    const day = String(d.getDate()).padStart(2, '0');
    return `${y}-${m}-${day}`;
}

function parseDate(s) {
    const [y, m, d] = s.split('-').map(Number);
    return new Date(y, m - 1, d);
}

function daysBetween(a, b) {
    return Math.round((parseDate(b) - parseDate(a)) / 86400000) + 1;
}

function dateRange(start, end) {
    const dates = [];
    let d = parseDate(start);
    const e = parseDate(end);
    while (d <= e) {
        dates.push(formatDate(d));
        d.setDate(d.getDate() + 1);
    }
    return dates;
}

function isDateTaken(dateKey) {
    // Scheduled in DB or assigned to an existing batch
    if (scheduledSet.has(dateKey)) return true;
    for (const b of batches) {
        const dates = dateRange(b.start_date, b.end_date);
        if (dates.includes(dateKey)) return true;
    }
    return false;
}

function getBatchForDate(dateKey) {
    for (const b of batches) {
        const dates = dateRange(b.start_date, b.end_date);
        if (dates.includes(dateKey)) return b;
    }
    return null;
}

function showStep(stepId) {
    document.querySelectorAll('.wizard-step').forEach(el => el.classList.remove('active'));
    document.getElementById(stepId).classList.add('active');
}

function getDiffEmojis(count) {
    const map = { Easy: '🟢', Medium: '🟡', Hard: '🔴' };
    return Array.from({ length: count }, (_, i) =>
        map[DIFFICULTY_CYCLE[i % DIFFICULTY_CYCLE.length]]
    ).join('');
}

function getDiffList(count) {
    return Array.from({ length: count }, (_, i) =>
        DIFFICULTY_CYCLE[i % DIFFICULTY_CYCLE.length]
    ).join(', ');
}

function formatShortDate(dateStr) {
    const d = parseDate(dateStr);
    const months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
    return `${months[d.getMonth()]} ${d.getDate()}`;
}

// ─────────────────────────────────────────────
// Calendar rendering
// ─────────────────────────────────────────────

function renderCalendar() {
    const grid = document.getElementById('calGrid');
    const year = DATA.year;
    const month = DATA.month;

    // Get first day of month (0=Sun, convert to Mon=0)
    const firstDay = new Date(year, month - 1, 1);
    const startDow = (firstDay.getDay() + 6) % 7; // Monday=0
    const daysInMonth = new Date(year, month, 0).getDate();
    const today = formatDate(new Date());

    let html = '';

    // Pad beginning with empty cells
    for (let i = 0; i < startDow; i++) {
        html += '<div class="gcal-cell gcal-empty"></div>';
    }

    // Day cells
    for (let day = 1; day <= daysInMonth; day++) {
        const dateKey = `${year}-${String(month).padStart(2, '0')}-${String(day).padStart(2, '0')}`;
        const isScheduled = scheduledSet.has(dateKey);
        const batch = getBatchForDate(dateKey);
        const isToday = dateKey === today;

        // Selection state
        let inSelection = false;
        if (selectionStart && selectionEnd) {
            const selDates = dateRange(
                selectionStart <= selectionEnd ? selectionStart : selectionEnd,
                selectionStart <= selectionEnd ? selectionEnd : selectionStart
            );
            inSelection = selDates.includes(dateKey);
        } else if (selectionStart && dateKey === selectionStart) {
            inSelection = true;
        }

        let cls = 'gcal-cell';
        let style = '';

        if (isScheduled) {
            cls += ' gcal-scheduled';
        } else if (batch) {
            cls += ' gcal-batched';
            style = `border-color: ${batch.color}; background: ${batch.color}15;`;
        } else {
            cls += ' gcal-open';
        }

        if (inSelection) cls += ' gcal-selected';
        if (isToday) cls += ' gcal-today';

        const batchLabel = batch
            ? `<span class="gcal-batch-label" style="background:${batch.color};">${batch.auto ? '🤖' : batch.theme.slice(0, 6)}</span>`
            : '';

        html += `<div class="${cls}" style="${style}" data-date="${dateKey}" onclick="onDateClick('${dateKey}')">
            <span class="gcal-day">${day}</span>
            ${isScheduled ? '<span class="gcal-sched-dot">●</span>' : ''}
            ${batchLabel}
        </div>`;
    }

    // Pad end
    const totalCells = startDow + daysInMonth;
    const remainder = totalCells % 7;
    if (remainder > 0) {
        for (let i = 0; i < 7 - remainder; i++) {
            html += '<div class="gcal-cell gcal-empty"></div>';
        }
    }

    grid.innerHTML = html;
}

// ─────────────────────────────────────────────
// Date click handler
// ─────────────────────────────────────────────

function onDateClick(dateKey) {
    // Can't select scheduled dates or dates in existing batches
    if (scheduledSet.has(dateKey) || getBatchForDate(dateKey)) return;

    if (!selectionStart) {
        // First click — start selection
        selectionStart = dateKey;
        selectionEnd = dateKey;
    } else if (selectionStart && !selectionEnd || selectionStart === selectionEnd) {
        // Second click — set end date
        let start = selectionStart;
        let end = dateKey;

        // Ensure start <= end
        if (start > end) { [start, end] = [end, start]; }

        // Check max 7 days
        const count = daysBetween(start, end);
        if (count > 7) {
            // Clamp to 7 days from start
            const clamped = parseDate(start);
            clamped.setDate(clamped.getDate() + 6);
            end = formatDate(clamped);
        }

        // Check no scheduled dates in range
        const range = dateRange(start, end);
        const hasConflict = range.some(d => scheduledSet.has(d) || getBatchForDate(d));
        if (hasConflict) {
            selectionStart = null;
            selectionEnd = null;
            renderCalendar();
            return;
        }

        selectionStart = start;
        selectionEnd = end;
    } else {
        // Third click — reset and start new selection
        selectionStart = dateKey;
        selectionEnd = dateKey;
    }

    renderCalendar();
    updateSelectionBanner();
}

function updateSelectionBanner() {
    const banner = document.getElementById('selectionBanner');

    if (!selectionStart) {
        banner.style.display = 'none';
        return;
    }

    const start = selectionStart <= selectionEnd ? selectionStart : selectionEnd;
    const end = selectionStart <= selectionEnd ? selectionEnd : selectionStart;
    const count = daysBetween(start, end);

    document.getElementById('selRange').textContent = `${formatShortDate(start)} → ${formatShortDate(end)}`;
    document.getElementById('selCount').textContent = `${count} day${count > 1 ? 's' : ''}`;
    banner.style.display = '';
}

function cancelSelection() {
    selectionStart = null;
    selectionEnd = null;
    renderCalendar();
    document.getElementById('selectionBanner').style.display = 'none';
}

// ─────────────────────────────────────────────
// Confirm batch
// ─────────────────────────────────────────────

function confirmBatch() {
    if (!selectionStart || !selectionEnd) return;

    const start = selectionStart <= selectionEnd ? selectionStart : selectionEnd;
    const end = selectionStart <= selectionEnd ? selectionEnd : selectionStart;
    const count = daysBetween(start, end);

    const mode = document.getElementById('selThemeMode').value;
    const themeName = document.getElementById('selThemeName').value.trim();

    const batch = {
        id: Date.now(),
        start_date: start,
        end_date: end,
        count: count,
        theme: mode === 'manual' ? themeName : '',
        auto: mode === 'auto',
        color: BATCH_COLORS[batches.length % BATCH_COLORS.length],
    };

    batches.push(batch);

    // Reset selection
    selectionStart = null;
    selectionEnd = null;
    document.getElementById('selectionBanner').style.display = 'none';
    document.getElementById('selThemeMode').value = 'auto';
    document.getElementById('selThemeName').value = '';
    document.getElementById('selThemeName').style.display = 'none';

    renderCalendar();
    renderBatchList();
}

// ─────────────────────────────────────────────
// Batch list
// ─────────────────────────────────────────────

function removeBatch(batchId) {
    batches = batches.filter(b => b.id !== batchId);
    batches.forEach((b, i) => b.color = BATCH_COLORS[i % BATCH_COLORS.length]);
    renderCalendar();
    renderBatchList();
}

function renderBatchList() {
    const list = document.getElementById('batchList');
    const summary = document.getElementById('batchSummary');

    if (batches.length === 0) {
        list.innerHTML = '<p class="muted" style="text-align:center; padding:16px;">Click dates on the calendar to start.</p>';
        summary.style.display = 'none';
        return;
    }

    list.innerHTML = batches.map((b, i) => `
        <div class="batch-card" style="border-left: 3px solid ${b.color};">
            <div class="batch-card-header">
                <span class="batch-num" style="background: ${b.color};">${i + 1}</span>
                <span class="batch-dates">${formatShortDate(b.start_date)} → ${formatShortDate(b.end_date)}</span>
                <button class="batch-remove" onclick="removeBatch(${b.id})" title="Remove">✕</button>
            </div>
            <div class="batch-card-body">
                <span class="batch-theme">${b.auto ? '🤖 Auto' : '✍️ ' + b.theme}</span>
                <span class="batch-count">${b.count}d</span>
                <span class="batch-diff">${getDiffEmojis(b.count)}</span>
            </div>
        </div>
    `).join('');

    const totalP = batches.reduce((sum, b) => sum + b.count, 0);
    document.getElementById('totalBatches').textContent = batches.length;
    document.getElementById('totalProblems').textContent = totalP;
    summary.style.display = '';
}

// ── Runner step (Step-by-Step Execution) ──

let currentBatchIdx = 0;
let batchStatuses = []; // Array of 'pending', 'running', 'done', 'error'
let batchResults = []; // Array of result objects or null
let executedThemes = []; // To track themes generated in this session

function switchToRunner() {
    if (batches.length === 0) return;

    // Reset state if starting fresh
    if (batchStatuses.length !== batches.length) {
        batchStatuses = new Array(batches.length).fill('pending');
        batchResults = new Array(batches.length).fill(null);
        currentBatchIdx = 0;
        executedThemes = [];
    }

    renderRunnerQueue();
    renderRunnerCard();
    showStep('stepRunner');
}

function renderRunnerQueue() {
    const list = document.getElementById('runnerList');
    list.innerHTML = batches.map((b, i) => {
        const status = batchStatuses[i];
        let icon = '○';
        if (status === 'running') icon = '⏳';
        if (status === 'done') icon = '✅';
        if (status === 'error') icon = '❌';

        // Check locked state: locked if previous batch not done
        const isLocked = i > 0 && batchStatuses[i - 1] !== 'done';
        if (isLocked && status === 'pending') icon = '🔒';

        const activeClass = i === currentBatchIdx ? 'active' : '';
        const statusClass = status; // pending, running, done, error
        const lockedClass = isLocked ? 'locked' : '';

        return `
        <div class="runner-item ${activeClass} ${statusClass} ${lockedClass}" onclick="selectBatch(${i})">
            <div>
                <span style="font-weight:700; color:${b.color}; margin-right:6px;">${i + 1}</span>
                <span>${formatShortDate(b.start_date)}</span>
            </div>
            <div>${icon}</div>
        </div>`;
    }).join('');
}

function selectBatch(i) {
    // Allows viewing any batch, even locked ones
    currentBatchIdx = i;
    renderRunnerQueue();
    renderRunnerCard();
}

function renderRunnerCard() {
    const container = document.getElementById('runnerCard');
    const b = batches[currentBatchIdx];
    if (!b) return;

    const status = batchStatuses[currentBatchIdx];
    const result = batchResults[currentBatchIdx];

    // Check locked state
    const isLocked = currentBatchIdx > 0 && batchStatuses[currentBatchIdx - 1] !== 'done';

    // Themes to avoid
    const avoids = [...DATA.recentThemes, ...executedThemes];

    const promptPreview = b.auto
        ? `Recent themes to avoid:\n${avoids.join(', ') || '(none)'}\n\nPick ONE creative theme for coding problems (WeeklyTheme).`
        : `Manual Theme: "${b.theme}"\n\nGenerate problems for this theme.`;

    let actionButton = '';

    if (status === 'pending' || status === 'error') {
        if (isLocked) {
            actionButton = `<button class="btn btn-secondary" disabled title="Complete previous batch first">🔒 Locked (Finish Batch ${currentBatchIdx})</button>`;
        } else {
            const btnLabel = status === 'error' ? 'Retry Batch' : '🚀 Run Batch ' + (currentBatchIdx + 1);
            actionButton = `<button class="btn btn-primary" onclick="runSingleBatch(${currentBatchIdx})">${btnLabel}</button>`;
        }
    } else if (status === 'running') {
        actionButton = `<button class="btn btn-secondary" disabled>Generating...</button>`;
    } else if (status === 'done') {
        if (currentBatchIdx < batches.length - 1) {
            // Check if next batch is locked? It shouldn't be, because this one is done.
            // But we render the button to switch view.
            actionButton = `<button class="btn btn-accent" onclick="selectBatch(${currentBatchIdx + 1})">Next Batch →</button>`;
        } else {
            actionButton = `<a href="/" class="btn btn-accent">🎉 Finish & View Calendar</a>`;
        }
    }

    let resultHtml = '';
    if (result) {
        if (result.error) {
            resultHtml = `<div class="progress-item error">❌ Error: ${result.error}</div>`;
        } else {
            // Fix: Use result.problems_created instead of result.problem_count
            resultHtml = `
            <div class="result-box">
                <h3>✅ Generated: ${result.theme}</h3>
                <div class="result-problems">
                    ${result.problems_created} problems created for ${result.date_range}
                </div>
            </div>`;
        }
    }

    container.innerHTML = `
        <div class="batch-detail-header">
             <div style="display:flex; align-items:center; gap:12px;">
                <span class="batch-num" style="background: ${b.color}; padding: 4px 10px; border-radius:4px; color:#fff; font-weight:bold;">${currentBatchIdx + 1}</span>
                <h2>${formatShortDate(b.start_date)} — ${formatShortDate(b.end_date)}</h2>
                ${isLocked ? '<span style="font-size:0.8rem; color:var(--text-muted); border:1px solid var(--border); padding:2px 6px; border-radius:4px;">Locked</span>' : ''}
            </div>
            <div class="batch-detail-meta" style="margin-top:8px;">
                ${b.count} days • ${b.auto ? '🤖 AI Auto-Pick' : '✍️ ' + b.theme} • Diff: ${getDiffEmojis(b.count)}
            </div>
        </div>

        <div class="prompt-preview-container">
            <h4>Prompt Context / Preview</h4>
            <div class="prompt-preview">${promptPreview}</div>
        </div>

        ${resultHtml}

        <div class="runner-actions">
            ${actionButton}
        </div>
    `;
}

async function runSingleBatch(i) {
    // Security check for lock
    if (i > 0 && batchStatuses[i - 1] !== 'done') {
        alert("Please complete the previous batch first.");
        return;
    }

    const b = batches[i];
    batchStatuses[i] = 'running';
    renderRunnerQueue();
    renderRunnerCard();

    const payload = {
        batches: [{
            start_date: b.start_date,
            count: b.count,
            theme: b.auto ? '' : b.theme,
        }],
        // We might want to pass excluded themes explicitly if backend doesn't check 'executedThemes' automatically?
        // But backend checks DB. 'executedThemes' are in DB if prev batches succeeded.
    };

    try {
        const resp = await fetch('/api/generate', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload),
        });

        if (!resp.ok) throw new Error(`Server error ${resp.status}`);
        const data = await resp.json();

        // Result is a list of results (length 1)
        const res = data.results[0];

        if (res.error) {
            batchStatuses[i] = 'error';
            batchResults[i] = { error: res.error };
        } else {
            batchStatuses[i] = 'done';
            batchResults[i] = res;
            // Add to executed themes for future batches to see
            executedThemes.push(res.theme);
        }

    } catch (err) {
        batchStatuses[i] = 'error';
        batchResults[i] = { error: err.message };
    }

    renderRunnerQueue();
    renderRunnerCard();
}


// ─────────────────────────────────────────────
// Init
// ─────────────────────────────────────────────

document.addEventListener('DOMContentLoaded', () => {
    // Selection banner controls
    document.getElementById('selThemeMode').addEventListener('change', (e) => {
        document.getElementById('selThemeName').style.display =
            e.target.value === 'manual' ? '' : 'none';
    });
    document.getElementById('confirmBatchBtn').addEventListener('click', confirmBatch);
    document.getElementById('cancelSelBtn').addEventListener('click', cancelSelection);

    // Wizard navigation
    document.getElementById('toReviewBtn').addEventListener('click', switchToRunner);
    // Back button in runner
    document.getElementById('backToPlanBtn').addEventListener('click', () => showStep('stepPlan'));

    renderCalendar();
    renderBatchList();
});
