/* TRAINER BOOKING LOGIC */
let selectedSlotId = null;

function bookSlot(slotId, isBooked) {
    if (isBooked === 'True') return;
    
    selectedSlotId = slotId;
    document.getElementById('bookingModal').style.display = 'block';
}

function closeModal() {
    document.getElementById('bookingModal').style.display = 'none';
    selectedSlotId = null;
}

document.addEventListener('DOMContentLoaded', () => {
    const confirmBtn = document.getElementById('confirmBtn');
    if (confirmBtn) {
        confirmBtn.addEventListener('click', async () => {
            if (!selectedSlotId) return;
            
            try {
                const res = await fetch('/api/book-slot', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ slot_id: selectedSlotId })
                });
                const data = await res.json();
                
                if (data.success) {
                    showToast('Tactical uplink established ✅', 'success');
                    setTimeout(() => window.location.reload(), 1000);
                } else {
                    showToast(data.error || 'Uplink failed', 'error');
                }
            } catch (err) {
                console.error('Network error during booking:', err);
                showToast('Neural link failure ⚠️', 'error');
            }
        });
    }

    // Handle Cancellation on Dashboard
    const cancelBtns = document.querySelectorAll('.cancel-session-btn');
    cancelBtns.forEach(btn => {
        btn.addEventListener('click', async (e) => {
            const slotId = btn.getAttribute('data-id');
            // Execute directly with toast feedback (Premium feel)
            if (true) { 
                try {
                    const res = await fetch('/api/cancel-slot', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ slot_id: slotId })
                    });
                    const data = await res.json();
                    
                    if (data.success) {
                        showToast('Tactical link severed 🗑️', 'info');
                        setTimeout(() => window.location.reload(), 1000);
                    } else {
                        showToast(data.error || 'Cancellation failed', 'error');
                    }
                } catch (err) {
                    console.error('Network error during cancellation:', err);
                }
            }
        });
    });
});
