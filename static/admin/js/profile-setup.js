/* PROFILE SETUP LOGIC */
document.addEventListener('DOMContentLoaded', () => {
    const profileForm = document.getElementById('profileForm');
    const alertBox = document.getElementById('alertBox');

    const showAlert = (message) => {
        if (alertBox) {
            alertBox.style.display = 'block';
            alertBox.textContent = message;
            setTimeout(() => { alertBox.style.display = 'none'; }, 5000);
        }
    };

    if (profileForm) {
        profileForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            const formData = {
                age: document.getElementById('age').value,
                gender: document.getElementById('gender').value,
                height: document.getElementById('height').value,
                weight: document.getElementById('weight').value,
                goal: document.getElementById('goal').value,
            };

            try {
                const res = await fetch('/api/profile', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(formData)
                });
                const data = await res.json();
                if (data.success) {
                    window.location.href = data.redirect;
                } else {
                    showAlert(data.error || 'Profile setup failed');
                }
            } catch (err) {
                showAlert('Network error during calibration');
            }
        });
    }
});
