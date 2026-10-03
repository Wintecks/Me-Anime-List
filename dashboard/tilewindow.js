const openBtn = document.getElementById("opentilewindowbtn");
const closeBtn = document.getElementById("tilewindow_btnclose");
const cencleBtn = document.getElementById("tilewindow_btncencle");
const tileCreateWindow = document.getElementById("tilewindow");
const createTileForm = document.getElementById("tilewindow_form");
const bodyBox = document.getElementById("bodybox");

function openTileWindow() {
    tileCreateWindow.classList.add('active');
}
openBtn.addEventListener('click', openTileWindow);

function closeTileWindow() {
    tileCreateWindow.classList.remove('active');
    createTileForm.reset();
}
closeBtn.addEventListener('click', closeTileWindow);
cencleBtn.addEventListener('click', closeTileWindow);

tileCreateWindow.addEventListener('click', (e) => {
    if (e.target === tileCreateWindow) closeTileWindow();
});

document.addEventListener('DOMContentLoaded', loadTile)

async function loadTile () {
    try {
        const response = await fetch("api/tiles");
        const tiles = await response.json();
        bodyBox.innerHTML = "";
        tiles.forEach(tile => renderTile(tile));
    }   catch (error) {
        console.error('Помилка завантаження плиток зі сервера:', error);
    }
}

createTileForm.addEventListener('submit', async (e) => {
    e.preventDefault();

    const title = document.getElementById("tilewindow_tiletitle").value;
    const desc = document.getElementById("tilewindow_tiledesc").value;
    const url = document.getElementById("tilewindow_tileurl").value;

    const newTile = {
        id: Date.now(),
        title,
        desc,
        url
    };

    try {
        const response = await fetch("/api/tiles", {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify(newTile)
        })

        if (response.ok) {
            const savedTile = await response.json();
            renderTile(savedTile);
            createTileForm.reset();
            closeTileWindow();
        }
    } catch (error) {
        console.error('Помилка збереження плитки:', error);
    }
});

function renderTile(tile) {
    const card = document.createElement('a');
    card.className = 'tilecard';
    card.href = tile.url;
    card.target = '_blank';
    card.rel = 'noopener noreferrer';
    
    card.innerHTML = `
        <h4>${tile.title}</h4>
        <p>${tile.desc || ''}</p>
    `;
    bodyBox.appendChild(card);

    closeTileWindow()
}