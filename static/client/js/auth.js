/* AUTH PAGE LOGIC */
document.addEventListener('DOMContentLoaded', () => {
    const authForm = document.getElementById('authForm');
    const alertBox = document.getElementById('alertBox');

    window.showAlert = (message) => {
        if (alertBox) {
            alertBox.classList.add('visible');
            alertBox.textContent = message;
            setTimeout(() => { alertBox.classList.remove('visible'); }, 5000);
        }
    };

    if (authForm) {
        authForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            const mode = authForm.dataset.mode;
            const email = document.getElementById('email').value;
            const password = document.getElementById('password').value;
            let name;
            
            if (mode === 'signup') {
                const nameEl = document.getElementById('name');
                if (nameEl) name = nameEl.value;
            }

            try {
                const res = await fetch('/api/auth', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ action: mode, email, password, name })
                });
                const data = await res.json();
                if (data.success) {
                    window.location.href = data.redirect;
                } else {
                    showAlert(data.error || 'Authentication failed');
                }
            } catch (err) {
                showAlert('Protocol error: Signal lost');
            }
        });
    }
});
