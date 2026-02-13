/**
 * Editor — serialize test cases to JSON before form submit.
 */

document.addEventListener('DOMContentLoaded', () => {
    const form = document.getElementById('editorForm');
    const jsonField = document.getElementById('testCasesJson');
    const list = document.getElementById('testCasesList');
    const addBtn = document.getElementById('addTestCase');

    if (!form) return;

    // ── Serialize test cases on submit ──
    form.addEventListener('submit', () => {
        const cards = list.querySelectorAll('.tc-card');
        const testCases = [];

        cards.forEach(card => {
            testCases.push({
                type: card.querySelector('[data-field="type"]').value,
                input: card.querySelector('[data-field="input"]').value,
                expected: card.querySelector('[data-field="expected"]').value,
                hint: card.querySelector('[data-field="hint"]').value,
            });
        });

        jsonField.value = JSON.stringify(testCases);
    });

    // ── Add test case ──
    addBtn.addEventListener('click', () => {
        const count = list.querySelectorAll('.tc-card').length;
        const card = document.createElement('div');
        card.className = 'tc-card';
        card.dataset.index = count;
        card.innerHTML = `
            <div class="tc-header">
                <span class="tc-num">#${count + 1}</span>
                <select class="tc-type" data-field="type">
                    <option value="basic">Basic</option>
                    <option value="edge">Edge</option>
                    <option value="logic">Logic</option>
                    <option value="conciseness">Conciseness</option>
                </select>
                <button type="button" class="btn-icon btn-delete-tc" title="Remove">×</button>
            </div>
            <div class="tc-body">
                <label>Input</label>
                <input type="text" data-field="input" class="tc-input" placeholder='e.g. [1, 2, 3]'>
                <label>Expected</label>
                <input type="text" data-field="expected" class="tc-input" placeholder='e.g. 6'>
                <label>Hint</label>
                <input type="text" data-field="hint" class="tc-input" placeholder='Helpful hint...'>
            </div>
        `;
        list.appendChild(card);
        bindDeleteButton(card);
    });

    // ── Delete test case ──
    function bindDeleteButton(card) {
        const btn = card.querySelector('.btn-delete-tc');
        if (btn) {
            btn.addEventListener('click', () => {
                card.remove();
                renumberCards();
            });
        }
    }

    function renumberCards() {
        const cards = list.querySelectorAll('.tc-card');
        cards.forEach((card, i) => {
            card.querySelector('.tc-num').textContent = `#${i + 1}`;
            card.dataset.index = i;
        });
    }

    // Bind existing delete buttons
    list.querySelectorAll('.tc-card').forEach(bindDeleteButton);
});
