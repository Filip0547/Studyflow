// Flashcard functionality
let currentCardIndex = 0;
let words = [];
let showAnswer = false;

function initFlashcards() {
    const studySection = document.getElementById('study-section');
    if (!studySection) return;

    // Get words from the table
    const tableRows = document.querySelectorAll('.study-table tbody tr');
    words = Array.from(tableRows).map(row => {
        const cells = row.querySelectorAll('td');
        return {
            word: cells[1].textContent.trim(),
            description: cells[2].textContent.trim(),
            example: cells[3].textContent.trim(),
            disadvantage: cells[4].textContent.trim()
        };
    });

    if (words.length === 0) return;

    showCard();
}

function showCard() {
    const card = document.getElementById('flashcard');
    const wordEl = document.getElementById('card-word');
    const answerEl = document.getElementById('card-answer');
    const prevBtn = document.getElementById('prev-card');
    const nextBtn = document.getElementById('next-card');
    const toggleBtn = document.getElementById('toggle-answer');

    if (words.length === 0) return;

    const currentWord = words[currentCardIndex];
    wordEl.textContent = currentWord.word;
    if (showAnswer) {
        answerEl.innerHTML = `
            <strong>Description:</strong> ${currentWord.description || '—'}<br>
            <strong>Example:</strong> ${currentWord.example || '—'}<br>
            <strong>Disadvantage:</strong> ${currentWord.disadvantage || '—'}
        `;
        toggleBtn.textContent = 'Hide Answer';
    } else {
        answerEl.innerHTML = '';
        toggleBtn.textContent = 'Show Answer';
    }

    prevBtn.disabled = currentCardIndex === 0;
    nextBtn.disabled = currentCardIndex === words.length - 1;
}

function nextCard() {
    if (currentCardIndex < words.length - 1) {
        currentCardIndex++;
        showAnswer = false;
        showCard();
    }
}

function prevCard() {
    if (currentCardIndex > 0) {
        currentCardIndex--;
        showAnswer = false;
        showCard();
    }
}

function toggleAnswer() {
    showAnswer = !showAnswer;
    showCard();
}

document.addEventListener('DOMContentLoaded', () => {
    initFlashcards();

    // Event listeners for flashcard buttons
    const prevBtn = document.getElementById('prev-card');
    const nextBtn = document.getElementById('next-card');
    const toggleBtn = document.getElementById('toggle-answer');

    if (prevBtn) prevBtn.addEventListener('click', prevCard);
    if (nextBtn) nextBtn.addEventListener('click', nextCard);
    if (toggleBtn) toggleBtn.addEventListener('click', toggleAnswer);

    // initialize any dropdowns on dashboard
    initDropdowns();
});

// initialize dropdown menus used on the dashboard
function initDropdowns() {
    document.querySelectorAll('.dropdown-toggle').forEach(button => {
        button.addEventListener('click', function(e) {
            e.preventDefault();
            const dropdownId = this.getAttribute('data-dropdown');
            const dropdown = document.getElementById(dropdownId);

            // close other open dropdowns
            document.querySelectorAll('.dropdown-content.show').forEach(el => {
                if (el.id !== dropdownId) {
                    el.classList.remove('show');
                }
            });

            // toggle this dropdown
            dropdown.classList.toggle('show');
            this.classList.toggle('active');
        });
    });

    document.addEventListener('click', function(e) {
        if (!e.target.closest('.dropdown-menu')) {
            document.querySelectorAll('.dropdown-content.show').forEach(el => {
                el.classList.remove('show');
            });
            document.querySelectorAll('.dropdown-toggle.active').forEach(btn => {
                btn.classList.remove('active');
            });
        }
    });
}