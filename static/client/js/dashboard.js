/* NYX DASHBOARD — COMMAND CENTER JS */
document.addEventListener('DOMContentLoaded', () => {

    // ── LOGOUT HANDLERS ──
    const logoutBtns = ['dashLogout', 'logoutBtn'];
    logoutBtns.forEach(id => {
        const btn = document.getElementById(id);
        if (btn) {
            btn.addEventListener('click', async (e) => {
                e.preventDefault();
                try {
                    await fetch('/api/logout', { method: 'POST' });
                    window.location.href = '/auth?mode=login';
                } catch (err) { console.error('Logout failed', err); }
            });
        }
    });

    // ── TIME TOGGLE ──
    document.querySelectorAll('.time-toggle span').forEach(span => {
        span.addEventListener('click', () => {
            document.querySelectorAll('.time-toggle span').forEach(s => s.classList.remove('active'));
            span.classList.add('active');
        });
    });

    // ── NUMBER ANIMATION HELPER ──
    const animateValue = (id, end, duration = 1000) => {
        const obj = document.getElementById(id);
        if (!obj) return;
        const start = 0;
        const startTime = performance.now();
        
        const step = (currentTime) => {
            const progress = Math.min((currentTime - startTime) / duration, 1);
            const value = progress * (end - start) + start;
            
            if (id === 'stat-weight') {
                obj.textContent = value.toFixed(1);
            } else if (id === 'stat-steps') {
                obj.textContent = Math.floor(value).toLocaleString();
            }
            
            if (progress < 1) {
                requestAnimationFrame(step);
            }
        };
        requestAnimationFrame(step);
    };

    // Trigger animations on load
    const wVal = parseFloat(document.getElementById('stat-weight')?.textContent || 0);
    const sVal = parseInt(document.getElementById('stat-steps')?.textContent?.replace(/,/g, '') || 0);
    
    setTimeout(() => {
        animateValue('stat-weight', wVal, 1200);
        animateValue('stat-steps', sVal, 1800);
    }, 300);

    // ── LOG DAILY PROTOCOL ──
    const logForm = document.getElementById('logForm');
    if (logForm) {
        logForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            const weight = document.getElementById('logWeight')?.value;
            const steps  = document.getElementById('logSteps')?.value;
            if (!weight && !steps) return;
            
            const btn = logForm.querySelector('.db-submit-btn');
            const originalHTML = btn.innerHTML;
            
            try {
                btn.innerHTML = '<i class="ph-bold ph-spinner ph-spin"></i> UPLOADING...';
                const res = await fetch('/api/log', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ weight, steps })
                });
                if (res.ok) {
                    btn.innerHTML = '<i class="ph-bold ph-check"></i> PROTOCOL SYNCED';
                    btn.style.background = 'var(--accent)';
                    btn.style.color = '#fff';
                    setTimeout(() => {
                        window.location.reload(); 
                    }, 1500);
                }
            } catch (err) { 
                console.error('Log submission failed:', err); 
                btn.innerHTML = originalHTML;
            }
        });
    }

});
