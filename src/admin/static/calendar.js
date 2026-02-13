/**
 * Calendar interactivity — drag-and-drop problem moving.
 */

document.addEventListener('DOMContentLoaded', () => {
    const cells = document.querySelectorAll('.day-cell');
    let draggedDate = null;

    cells.forEach(cell => {
        // ── Drag start ──
        cell.addEventListener('dragstart', (e) => {
            draggedDate = cell.dataset.date;
            cell.classList.add('dragging');
            e.dataTransfer.effectAllowed = 'move';
            e.dataTransfer.setData('text/plain', draggedDate);
        });

        cell.addEventListener('dragend', () => {
            cell.classList.remove('dragging');
            document.querySelectorAll('.drag-over').forEach(c => c.classList.remove('drag-over'));
        });

        // ── Drop target ──
        cell.addEventListener('dragover', (e) => {
            e.preventDefault();
            const targetDate = cell.dataset.date;
            // Only allow drops on empty cells or different cells
            if (targetDate && targetDate !== draggedDate && !cell.classList.has?.('has-problem')) {
                e.dataTransfer.dropEffect = 'move';
                cell.classList.add('drag-over');
            }
        });

        cell.addEventListener('dragleave', () => {
            cell.classList.remove('drag-over');
        });

        cell.addEventListener('drop', async (e) => {
            e.preventDefault();
            cell.classList.remove('drag-over');

            const fromDate = e.dataTransfer.getData('text/plain');
            const toDate = cell.dataset.date;

            if (!fromDate || !toDate || fromDate === toDate) return;

            // Check if target already has a problem
            if (cell.classList.contains('has-problem')) {
                alert(`${toDate} already has a problem. Delete it first or pick an empty slot.`);
                return;
            }

            try {
                const res = await fetch('/api/move', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ from_date: fromDate, to_date: toDate }),
                });

                if (res.ok) {
                    // Reload to show updated state
                    window.location.reload();
                } else {
                    const data = await res.json();
                    alert(`Move failed: ${data.detail || 'Unknown error'}`);
                }
            } catch (err) {
                alert(`Network error: ${err.message}`);
            }
        });
    });
    // ── Theme editing ──
    document.addEventListener('click', async (e) => {
        const themeTag = e.target.closest('.theme-tag');
        if (!themeTag) return;

        const themeId = themeTag.dataset.id;
        const currentName = themeTag.querySelector('.theme-tag-name').textContent;

        const newName = prompt("Rename this theme:", currentName);
        if (!newName || newName === currentName) return;

        try {
            const res = await fetch('/api/theme/update', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ theme_id: themeId, new_theme: newName }),
            });

            if (res.ok) {
                window.location.reload();
            } else {
                const data = await res.json();
                alert(`Update failed: ${data.detail || 'Unknown error'}`);
            }
        } catch (err) {
            alert(`Network error: ${err.message}`);
        }
    });
});
