function openModal(modalId) {
    document.getElementById(modalId).style.display = 'flex';
}

function closeModal(modalId) {
    document.getElementById(modalId).style.display = 'none';
}

// Close modal when clicking outside
window.onclick = function (event) {
    if (event.target.classList.contains('modal-overlay')) {
        event.target.style.display = 'none';
    }
}

// Add smooth transitions to stat cards on load
document.addEventListener('DOMContentLoaded', () => {
    const cards = document.querySelectorAll('.kpi-card');
    cards.forEach((card, index) => {
        card.style.opacity = '0';
        card.style.transform = 'translateY(20px)';
        card.style.transition = 'all 0.5s ease-out';

        setTimeout(() => {
            card.style.opacity = '1';
            card.style.transform = 'translateY(0)';
        }, 100 * index);
    });

    // Start periodic KPI polling for a "Dynamic" experience
    if (window.location.pathname === '/dashboard') {
        setInterval(pollStats, 10000); // Every 10 seconds
    }
});

async function pollStats() {
    try {
        const response = await fetch('/api/stats');
        const data = await response.json();

        // Update Dashboard Elements if they exist
        const elements = {
            'active_fleet': data.active_fleet,
            'maintenance_alerts': data.maintenance_alerts,
            'pending_cargo': data.pending_cargo,
            'util_rate': data.util_rate + '%'
        };

        for (const [id, value] of Object.entries(elements)) {
            const el = document.querySelector(`.kpi-card[data-stat="${id}"] .kpi-value`);
            if (el && el.innerText !== value.toString()) {
                el.classList.add('pulse');
                el.innerText = value;
                setTimeout(() => el.classList.remove('pulse'), 1000);
            }
        }
    } catch (err) {
        console.error('Failed to poll stats:', err);
    }
}
