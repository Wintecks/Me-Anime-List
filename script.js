const SCRIPT_URL = 'https://script.google.com/macros/s/AKfycbyMtmOp3rkQEJJb6mvpuIeL4dOIM377gEzsExRrXUj_c79C0BrHpB3TE1xdIHmcNDWX/exec';

let animeList = [];
let isEditMode = false;

async function loadAnime() {
    try {
    const response = await fetch(SCRIPT_URL);
    animeList = await response.json();
    console.log(animeList)
    renderList(animeList);
    } catch (err) {
    console.error("Помилка завантаження:", err);
    }
}

function normalizeStatus(status) {
    if (!status) return 'Переглянув';
    const clean = String(status).trim();
    if (clean === 'Переглянув') return 'Переглянув';
    return clean;
}

function getStatusClass(status) {
    const normalized = normalizeStatus(status);
    switch (normalized) {
    case 'Дивлюся': return 'tag-watching';
    case 'Закинув': return 'tag-dropped';
    case 'Нові серії': return 'tag-new-episode';
    case 'Переглянув':
    default: return 'tag-completed';
    }
}

function renderList(list) {
    const grid = document.getElementById('anime-grid');
    grid.innerHTML = '';

    list.forEach(anime => {
    const card = document.createElement('div');
    card.className = 'card';
    
    const hasUrl = anime.url && anime.url.trim() !== '';
    const statusText = normalizeStatus(anime.status);
    const statusClass = getStatusClass(statusText);
    let badgeClass = ''
    let badgeText = ''

    if (anime.url.includes('https://anitube.in.ua/')) {
        badgeClass = 'badge-anitube'
        badgeText = 'Anitube'
    } else if (anime.url.includes('https://t.me/')) {
        badgeClass = 'badge-tg'
        badgeText = 'Tg'
    } 

    card.innerHTML = `
        <div class="card-title">${anime.title}</div>
        <div class="card-footer">
        <div class="badge-group">
            <span class="card-badge ${statusClass}">${statusText}</span>
            ${hasUrl ? `<span class="card-badge ${badgeClass}">${badgeText}</span>` : ''}
        </div>
        </div>
    `;

    card.addEventListener('click', (e) => {
        if ((e.ctrlKey || e.metaKey) && hasUrl) {
        e.preventDefault();
        const newWin = window.open(anime.url, '_blank');
        if (newWin) newWin.focus();
        } else {
        openEditModal(anime);
        }
    });

    card.addEventListener('auxclick', (e) => {
        if (e.button === 1 && hasUrl) {
        e.preventDefault();
        const newWin = window.open(anime.url, '_blank');
        if (newWin) newWin.focus();
        }
    });

    grid.appendChild(card);
    });

    document.getElementById('anime-count').innerText = `${animeList.length}`
}

function filterAnime() {
    const query = document.getElementById('search').value.toLowerCase().trim();
    const selectedTag = document.getElementById('search-tegs').value;

    const filtered = animeList.filter(a => {
        const statusText = normalizeStatus(a.status);

        // 1. Перевірка тегу/статусу (з <select>)
        let matchesTag = true;
        if (selectedTag !== 'Усі') {
            matchesTag = (statusText === selectedTag);
        }

        // 2. Перевірка текстового пошуку
        let matchesSearch = true;
        if (query !== '') {
            const titleMatch = a.title && a.title.toLowerCase().includes(query);
            const statusMatch = a.status && String(a.status).toLowerCase().includes(query);
            const urlMatch = a.url && a.url.toLowerCase().includes(query);

            let specialTagMatch = false;
            if (query === 'anitube') {
                specialTagMatch = a.url && a.url.includes('anitube.in.ua');
            } else if (query === 'tg' || query === 'telegram') {
                specialTagMatch = a.url && a.url.includes('t.me');
            }

            matchesSearch = titleMatch || statusMatch || urlMatch || specialTagMatch;
        }

        // Елемент підходить, якщо відповідає І обраному тегу, І пошуковому запиту
        return matchesTag && matchesSearch;
    });

    renderList(filtered);
}

function openAddModal() {
    isEditMode = false;
    document.getElementById('modal-heading').innerText = "Додати нове аніме";
    document.getElementById('edit-row-index').value = '';
    document.getElementById('anime-title').value = '';
    document.getElementById('anime-status').value = 'Дивлюся';
    document.getElementById('anime-url').value = '';
    document.getElementById('anime-desc').value = '';
    document.getElementById('delete-btn').style.display = 'none';
    document.getElementById('modal').style.display = 'flex';
}

function openEditModal(anime) {
    isEditMode = true;
    document.getElementById('modal-heading').innerText = "Налаштування елемента";
    document.getElementById('edit-row-index').value = anime.rowIndex;
    document.getElementById('anime-title').value = anime.title;
    document.getElementById('anime-status').value = normalizeStatus(anime.status);
    document.getElementById('anime-url').value = anime.url || '';
    document.getElementById('anime-desc').value = anime.description;
    document.getElementById('delete-btn').style.display = 'block';
    document.getElementById('modal').style.display = 'flex';
}

function closeModal() {
    document.getElementById('modal').style.display = 'none';
}

async function sendRequest(payload) {
    return fetch(SCRIPT_URL, {
    method: 'POST',
    headers: { 'Content-Type': 'text/plain;charset=utf-8' },
    body: JSON.stringify(payload)
    });
}

async function saveAnime() {
    const title = document.getElementById('anime-title').value.trim();
    const status = document.getElementById('anime-status').value;
    const url = document.getElementById('anime-url').value.trim();
    const description = document.getElementById('anime-desc').value;
    const rowIndex = document.getElementById('edit-row-index').value;

    if (!title) return alert("Введіть назву!");

    const saveBtn = document.getElementById('save-btn');
    saveBtn.innerText = 'Збереження...';
    saveBtn.disabled = true;

    const payload = {
    action: isEditMode ? 'edit' : 'add',
    title: title,
    status: status,
    url: url,
    description: description,
    rowIndex: rowIndex
    };

    try {
    await sendRequest(payload);
    closeModal();
    await loadAnime();
    } catch (err) {
    console.error("Помилка:", err);
    alert("Помилка при збереженні!");
    } finally {
    saveBtn.innerText = 'Зберегти';
    saveBtn.disabled = false;
    }
}

async function deleteCurrentAnime() {
    const rowIndex = document.getElementById('edit-row-index').value;
    const title = document.getElementById('anime-title').value;

    if (!confirm(`Видалити "${title}"?`)) return;

    closeModal();

    try {
    await sendRequest({ action: 'delete', rowIndex: rowIndex });
    await loadAnime();
    } catch (err) {
    console.error("Помилка при видаленні:", err);
    }
}

loadAnime();