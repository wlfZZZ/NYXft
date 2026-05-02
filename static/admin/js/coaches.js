/* COACHES PAGE LOGIC - ONELOOK CHAT */
document.addEventListener('DOMContentLoaded', () => {
    // Auto-scroll terminal to bottom
    const chatArea = document.getElementById('chatArea');
    const scrollTerminal = () => {
        if (chatArea) {
            chatArea.scrollTop = chatArea.scrollHeight;
        }
    };
    scrollTerminal();

    const chatForm = document.getElementById('chatForm');
    if (chatForm) {
        chatForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            const textInput = document.getElementById('chatInput');
            const submitBtn = document.querySelector('.pill-send-btn');
            
            if (!textInput.value.trim()) return;

            // UI State: Sending
            const originalBtnContent = submitBtn.innerHTML;
            submitBtn.innerHTML = '<i class="ph-bold ph-circle-notch animate-spin"></i>';
            submitBtn.disabled = true;
            
            const formData = { text: textInput.value };

            try {
                const res = await fetch('/api/chat', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(formData)
                });
                const data = await res.json();
                
                if (data.success) {
                    // Quick reload to show the AI response and new bubble
                    window.location.reload();
                } else {
                    showToast(data.error || 'Signal interrupted', 'error');
                    submitBtn.innerHTML = originalBtnContent;
                    submitBtn.disabled = false;
                }
            } catch (err) {
                showToast('Fatal Error: Secure link severed', 'error');
                submitBtn.innerHTML = originalBtnContent;
                submitBtn.disabled = false;
            }
        });
    }

    // Upgrade Button logic removed
});
