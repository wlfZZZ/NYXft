/* ═══════════════════════════════════════════
   PR TRACKER — ELITE LOGIC ENGINE
   ═══════════════════════════════════════════ */

document.addEventListener('DOMContentLoaded', () => {

    /* ── LOG OUT ── */
    ['logoutBtn', 'dashLogout'].forEach(id => {
        const btn = document.getElementById(id);
        if (btn) btn.addEventListener('click', async (e) => {
            e.preventDefault();
            await fetch('/api/logout', { method: 'POST' });
            window.location.href = '/auth';
        });
    });

    /* ── ANIMATE CHART BARS on load ── */
    document.querySelectorAll('.prt-bar').forEach(bar => {
        const targetH = bar.style.height;
        bar.style.height = '4px';
        setTimeout(() => { bar.style.height = targetH; }, 100);
    });

    /* ── ANIMATE GOAL BARS on load ── */
    document.querySelectorAll('.prt-goal-fill, .prt-goal-bar-fill').forEach(bar => {
        const targetW = bar.style.width;
        bar.style.width = '0%';
        setTimeout(() => { bar.style.width = targetW; }, 150);
    });

    /* ── LOG FORM SUBMIT ── */
    const prForm = document.getElementById('prForm');
    const logBtn = document.getElementById('logBtn');

    if (prForm) {
        prForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            const exercise = document.getElementById('prExercise').value.trim();
            const weight   = parseFloat(document.getElementById('prWeight').value);
            const reps     = parseInt(document.getElementById('prReps').value);

            if (!exercise || !weight || !reps) return;

            logBtn.disabled = true;
            logBtn.innerHTML = '<i class="ph-bold ph-circle-notch ph-spin"></i> Logging...';

            try {
                const res = await fetch('/api/pr', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ exercise, weight, reps })
                });
                const data = await res.json();

                if (data.success) {
                    if (data.is_new_pr) {
                        showPRBanner(data.exercise, data.weight);
                    }
                    // Add row to table live
                    appendTableRow(data.exercise, weight, reps, data.is_new_pr);
                    // Update hero total logs counter
                    const totalLogsEl = document.querySelector('.prt-hero-card:nth-child(2) .prt-hero-val');
                    if (totalLogsEl) totalLogsEl.textContent = parseInt(totalLogsEl.textContent) + 1;
                    if (data.is_new_pr) {
                        const totalPrsEl = document.querySelector('.prt-hero-card:nth-child(1) .prt-hero-val');
                        if (totalPrsEl) totalPrsEl.textContent = parseInt(totalPrsEl.textContent) + 1;
                    }
                    // Update key lift display if it's a tracked exercise
                    updateKeyLift(data.exercise, weight);
                    prForm.reset();
                    logBtn.innerHTML = '<i class="ph-bold ph-check"></i> Logged!';
                    setTimeout(() => {
                        logBtn.disabled = false;
                        logBtn.innerHTML = '<i class="ph-bold ph-plus"></i> LOG';
                    }, 2000);
                } else {
                    showError(data.error || 'Failed to log. Try again.');
                    logBtn.disabled = false;
                    logBtn.innerHTML = '<i class="ph-bold ph-plus"></i> LOG';
                }
            } catch (err) {
                showError('Connection error. Please retry.');
                logBtn.disabled = false;
                logBtn.innerHTML = '<i class="ph-bold ph-plus"></i> LOG';
            }
        });
    }

    /* ── GOAL FORM SUBMIT ── */
    const goalForm = document.getElementById('goalForm');
    if (goalForm) {
        goalForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            const exercise = document.getElementById('goalExercise').value;
            const target   = parseFloat(document.getElementById('goalTarget').value);
            if (!exercise || !target) return;
            try {
                const res = await fetch('/api/pr/goal', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ exercise, target })
                });
                const data = await res.json();
                if (data.success) {
                    // Soft reload to show updated goal bars
                    window.location.reload();
                }
            } catch (err) {
                showError('Goal update failed.');
            }
        });
    }

    /* ── SHOW PR BANNER ── */
    function showPRBanner(exercise, weight) {
        const banner = document.getElementById('prBanner');
        const text   = document.getElementById('prBannerText');
        if (!banner || !text) return;
        text.textContent = `🔥 New PR! ${exercise} — ${weight}kg!`;
        banner.classList.remove('hidden');
        // Auto-dismiss after 6s
        setTimeout(() => banner.classList.add('hidden'), 6000);
    }

    /* ── APPEND ROW TO TABLE LIVE ── */
    function appendTableRow(exercise, weight, reps, isPR) {
        const tbody = document.querySelector('.prt-table tbody');
        if (!tbody) return;

        // Remove empty state row if present
        const emptyRow = tbody.querySelector('.prt-empty-row');
        if (emptyRow) emptyRow.parentElement.remove();

        const today = new Date().toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
        const tr = document.createElement('tr');
        tr.className = isPR ? 'prt-pr-row' : '';
        tr.innerHTML = `
            <td class="prt-date-cell">${today}</td>
            <td class="prt-exercise-cell">
                ${isPR ? '<i class="ph-fill ph-star prt-star-icon"></i>' : ''}
                ${escHtml(exercise)}
            </td>
            <td class="prt-weight-cell ${isPR ? 'prt-weight-pr' : ''}">${weight} kg</td>
            <td>${reps}x</td>
            <td>${isPR
                ? '<span class="prt-pill prt-pill-pr">🏆 New PR</span>'
                : '<span class="prt-pill prt-pill-ok">Logged</span>'
            }</td>
        `;
        // Animate in
        tr.style.opacity = '0';
        tr.style.transform = 'translateY(-8px)';
        tbody.prepend(tr);
        requestAnimationFrame(() => {
            tr.style.transition = 'all 0.3s ease';
            tr.style.opacity = '1';
            tr.style.transform = 'translateY(0)';
        });

        // Update count pill
        const pill = document.querySelector('.prt-count-pill');
        if (pill) {
            const match = pill.textContent.match(/\d+/);
            if (match) pill.textContent = `${parseInt(match[0]) + 1} entries`;
        }
    }

    /* ── UPDATE KEY LIFT DISPLAY ── */
    function updateKeyLift(exercise, weight) {
        const exLower = exercise.toLowerCase().trim();
        const liftRows = document.querySelectorAll('.prt-lift-row');
        liftRows.forEach(row => {
            const name = row.querySelector('.prt-lift-name');
            if (!name) return;
            if (name.textContent.trim().toLowerCase() === exLower) {
                const statsEl = row.querySelector('.prt-lift-stats');
                if (statsEl) {
                    const currentEl = statsEl.querySelector('.prt-lift-current');
                    if (currentEl) {
                        const prev = parseFloat(currentEl.textContent);
                        if (weight > prev) {
                            currentEl.textContent = `${weight}kg`;
                            currentEl.style.color = '#16a34a';
                            // Flash green
                            currentEl.style.transform = 'scale(1.1)';
                            setTimeout(() => { currentEl.style.transform = ''; }, 400);
                        }
                    }
                }
            }
        });

        // Update best lift hero card
        const bestEl = document.querySelector('.prt-hero-card:nth-child(3) .prt-hero-val');
        if (bestEl) {
            const currentBest = parseFloat(bestEl.textContent);
            if (weight > currentBest) {
                bestEl.innerHTML = `${weight}<span class="prt-hero-unit">kg</span>`;
            }
        }
    }

    /* ── HELPERS ── */
    function showError(msg) {
        const existing = document.querySelector('.prt-err-toast');
        if (existing) existing.remove();
        const toast = document.createElement('div');
        toast.className = 'prt-err-toast';
        toast.style.cssText = `
            position:fixed; bottom:24px; right:24px; z-index:9999;
            background:#ef4444; color:#fff; padding:12px 20px;
            border-radius:10px; font-weight:700; font-size:0.85rem;
            box-shadow:0 8px 24px rgba(239,68,68,0.3);
            animation: fadein 0.3s ease;
        `;
        toast.textContent = msg;
        document.body.appendChild(toast);
        setTimeout(() => toast.remove(), 4000);
    }

    function escHtml(str) {
        return str.replace(/[&<>"']/g, s => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[s]));
    }

});
