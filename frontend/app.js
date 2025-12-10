const chatContainer = document.getElementById('chat-container');
const chatForm = document.getElementById('chat-form');
const userInput = document.getElementById('user-input');

// URL du webhook n8n (Production)
const N8N_WEBHOOK_URL = 'http://localhost:5678/webhook/vaultflow-agent';

// Générer un sessionId unique pour la session actuelle
const SESSION_ID = 'session_' + Math.random().toString(36).substr(2, 9);

function addMessage(text, type) {
    const messageDiv = document.createElement('div');
    messageDiv.classList.add('message');
    messageDiv.classList.add(type === 'user' ? 'user-message' : 'ai-message');

    // Convert line breaks to <br> to handle LLM formatting properly
    messageDiv.innerHTML = text.replace(/\n/g, '<br>');

    chatContainer.appendChild(messageDiv);
    chatContainer.scrollTop = chatContainer.scrollHeight;
}

chatForm.addEventListener('submit', async (e) => {
    e.preventDefault();
    const message = userInput.value.trim();
    if (!message) return;

    // Ajouter le message de l'utilisateur à l'interface
    addMessage(message, 'user');
    userInput.value = '';

    // Message de chargement temporaire
    const loadingId = 'loading-' + Date.now();
    addMessage('L\'assistant réfléchit...', 'ai');
    const loadingMsg = chatContainer.lastElementChild;
    loadingMsg.id = loadingId;
    loadingMsg.style.opacity = '0.5';

    try {
        const response = await fetch(N8N_WEBHOOK_URL, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                message: message,
                sessionId: SESSION_ID
            })
        });

        if (!response.ok) throw new Error('Erreur réseau');

        const data = await response.json();

        // Retirer le message de chargement et afficher la réponse réelle
        loadingMsg.remove();

        // On récupère le champ original_text renvoyé par le dernier node n8n
        const aiResponse = data.original_text || data.output || "Désolé, je n'ai pas pu traiter votre demande.";
        addMessage(aiResponse, 'ai');

    } catch (error) {
        console.error('Error:', error);
        loadingMsg.remove();
        addMessage('Désolé, une erreur est survenue lors de la connexion à l\'agent (n8n est-il lancé ?).', 'ai');
    }
});

// --- LIVE DATABASE MONITOR ---
const dbViewer = document.getElementById('db-viewer');
const BACKEND_URL = 'http://localhost:8000/debug/db_status';

async function updateLiveDB() {
    try {
        const response = await fetch(BACKEND_URL);
        const cards = await response.json();

        dbViewer.innerHTML = cards.map(card => `
            <div class="card-record ${card.active ? '' : 'blocked'}">
                <div class="row"><span class="label">CARD:</span><span class="val">${card.card_number}</span></div>
                <div class="row"><span class="label">OWNER:</span><span class="val">${card.owner.split('@')[0]}***</span></div>
                <div class="row">
                    <span class="label">STATUS:</span>
                    <span class="val ${card.active ? 'tag-active' : 'tag-blocked'}">${card.active ? 'ACTIVE' : 'BLOCKED'}</span>
                </div>
                <div class="row" style="font-size: 9px; opacity: 0.7;">
                    <span class="val">${card.status_text}</span>
                </div>
            </div>
        `).join('');

    } catch (error) {
        dbViewer.innerHTML = '<p style="color: #ef4444;">Erreur: Impossible de connecter au backend Python (8000).</p>';
    }
}

// Rafraîchir toutes les 2 secondes
setInterval(updateLiveDB, 2000);
updateLiveDB();
