/* ══════════════════════════════════════════
   NYX ANALYTICS — CHART INITIALIZATION JS
   ══════════════════════════════════════════ */

document.addEventListener('DOMContentLoaded', () => {
    const dataEl = document.getElementById('analytics-data');
    if (!dataEl) return;
    
    const rawData = JSON.parse(dataEl.textContent);
    
    // ── CHART DEFAULTS ──
    Chart.defaults.font.family = "'Outfit', sans-serif";
    Chart.defaults.color = '#94a3b8';
    Chart.defaults.plugins.tooltip.backgroundColor = '#0f172a';
    Chart.defaults.plugins.tooltip.padding = 12;
    Chart.defaults.plugins.tooltip.cornerRadius = 12;
    Chart.defaults.plugins.tooltip.titleFont = { size: 13, weight: 800 };
    
    const ctxWeight = document.getElementById('weightChart')?.getContext('2d');
    const ctxCal = document.getElementById('calChart')?.getContext('2d');
    const ctxCorr = document.getElementById('correlationChart')?.getContext('2d');
    const ctxVolume = document.getElementById('volumeChart')?.getContext('2d');
    const ctxRadar = document.getElementById('radarChart')?.getContext('2d');

    // 1. Weight Trajectory (Starter+)
    if (ctxWeight) {
        new Chart(ctxWeight, {
            type: 'line',
            data: {
                labels: rawData.labels,
                datasets: [{
                    label: 'Mass (kg)',
                    data: rawData.weight,
                    borderColor: '#0f172a',
                    borderWidth: 3,
                    tension: 0.4,
                    pointRadius: 4,
                    pointBackgroundColor: '#fff',
                    pointBorderColor: '#0f172a',
                    pointBorderWidth: 2,
                    fill: true,
                    backgroundColor: 'rgba(15, 23, 42, 0.03)'
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: { legend: { display: false } },
                scales: { 
                    y: { grid: { borderDash: [5, 5] }, ticks: { font: { weight: 700 } } },
                    x: { grid: { display: false } }
                }
            }
        });
    }

    // 2. Caloric Density (Starter+)
    if (ctxCal) {
        new Chart(ctxCal, {
            type: 'bar',
            data: {
                labels: rawData.labels.slice(-7),
                datasets: [{
                    label: 'Steps',
                    data: rawData.steps.slice(-7),
                    backgroundColor: '#3b82f6',
                    borderRadius: 8,
                    barThickness: 20
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: { legend: { display: false } },
                scales: { 
                    y: { grid: { display: false }, ticks: { display: false } },
                    x: { grid: { display: false } }
                }
            }
        });
    }

    // 3. Correlation Logic (Pro/Elite)
    if (ctxCorr) {
        new Chart(ctxCorr, {
            type: 'line',
            data: {
                labels: rawData.labels,
                datasets: [
                    {
                        label: 'Mass',
                        data: rawData.weight,
                        borderColor: '#0f172a',
                        yAxisID: 'y'
                    },
                    {
                        label: 'Activity',
                        data: rawData.steps,
                        borderColor: '#3b82f6',
                        backgroundColor: 'rgba(59, 130, 246, 0.1)',
                        fill: true,
                        yAxisID: 'y1'
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    y: { type: 'linear', display: true, position: 'left' },
                    y1: { type: 'linear', display: true, position: 'right', grid: { drawOnChartArea: false } }
                }
            }
        });
    }

    // 4. Strength Distribution (Pro/Elite)
    if (ctxVolume) {
        const vData = rawData.volume;
        new Chart(ctxVolume, {
            type: 'doughnut',
            data: {
                labels: ['Push', 'Pull', 'Legs'],
                datasets: [{
                    data: [vData.Push, vData.Pull, vData.Legs],
                    backgroundColor: ['#0f172a', '#22c55e', '#3b82f6'],
                    borderWidth: 0,
                    cutout: '75%'
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: { legend: { position: 'bottom', labels: { usePointStyle: true, font: { weight: 700 } } } }
            }
        });
    }

    // 5. Strength Saturation (Elite)
    if (ctxRadar) {
        new Chart(ctxRadar, {
            type: 'radar',
            data: {
                labels: ['Bench', 'Squat', 'Deadlift', 'Press', 'Pullup'],
                datasets: [{
                    label: 'Saturation',
                    data: [85, 92, 78, 65, 88], // Placeholder logic for now
                    borderColor: '#22c55e',
                    backgroundColor: 'rgba(34, 197, 94, 0.2)',
                    pointBackgroundColor: '#22c55e'
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    r: { angleLines: { display: true }, suggestedMin: 0, suggestedMax: 100 }
                }
            }
        });
    }
});
