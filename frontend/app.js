const API_BASE_URL = 'https://api-helpdesk-5epp.onrender.com/api'; // URL oficial de produção no Render

document.addEventListener('DOMContentLoaded', () => {
    const form = document.getElementById('ticket-form');
    const loadTicketsBtn = document.getElementById('load-tickets-btn');

    form.addEventListener('submit', async (e) => {
        e.preventDefault();
        const description = document.getElementById('ticket-description').value;
        if (!description.trim()) return;

        await submitTicket(description);
    });

    loadTicketsBtn.addEventListener('click', loadRecentTickets);

    // Load tickets on initial page load
    loadRecentTickets();
});

async function submitTicket(description) {
    const resultDiv = document.getElementById('result-content');
    const loadingDiv = document.getElementById('loading');
    const submitBtn = document.querySelector('button[type="submit"]');

    // Show loading
    loadingDiv.classList.remove('hidden');
    resultDiv.innerHTML = '';
    submitBtn.disabled = true;

    try {
        const response = await fetch(`${API_BASE_URL}/chamados`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ descricao: description })
        });

        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }

        const data = await response.json();
        displayResult(data.data);

        // Clear form
        document.getElementById('ticket-description').value = '';

        // Refresh ticket list
        loadRecentTickets();

    } catch (error) {
        console.error("Error submitting ticket:", error);
        resultDiv.innerHTML = `<p style="color: red;">Erro ao enviar chamado. Tente novamente.</p>`;
    } finally {
        // Hide loading
        loadingDiv.classList.add('hidden');
        submitBtn.disabled = false;
    }
}

function displayResult(data) {
    const resultDiv = document.getElementById('result-content');

    const priorityColor = getPriorityColor(data.prioridade);

    resultDiv.innerHTML = `
        <div class="ticket-card" style="border-left-color: ${priorityColor}">
            <h3>Resultado da Triagem</h3>
            <p><strong>Categoria:</strong> ${data.categoria}</p>
            <p><strong>Prioridade:</strong> <span style="color: ${priorityColor}; font-weight: bold;">${data.prioridade}</span></p>
            <p><strong>Justificativa da IA:</strong> ${data.justificativa}</p>
            <hr>
            <p><small>ID do chamado: ${data.id || 'N/A'}</small></p>
        </div>
    `;
}

async function loadRecentTickets() {
    const feedDiv = document.getElementById('tickets-feed');
    feedDiv.innerHTML = '<p>Carregando chamados...</p>';

    try {
        const response = await fetch(`${API_BASE_URL}/chamados`);
        if (!response.ok) {
             throw new Error(`HTTP error! status: ${response.status}`);
        }

        const data = await response.json();
        displayTicketsFeed(data.data);
    } catch (error) {
        console.error("Error loading tickets:", error);
        feedDiv.innerHTML = `<p style="color: red;">Erro ao carregar chamados.</p>`;
    }
}

function displayTicketsFeed(tickets) {
    const feedDiv = document.getElementById('tickets-feed');
    feedDiv.innerHTML = '';

    if (!tickets || tickets.length === 0) {
        feedDiv.innerHTML = '<p>Nenhum chamado recente encontrado.</p>';
        return;
    }

    tickets.forEach(ticket => {
        const priorityColor = getPriorityColor(ticket.prioridade);
        const card = document.createElement('div');
        card.className = 'ticket-card feed-card';
        card.style.borderLeftColor = priorityColor;

        card.innerHTML = `
            <div class="feed-header">
                <strong>ID: #${ticket.id}</strong>
                <span class="badge" style="background-color: ${priorityColor}">${ticket.prioridade}</span>
            </div>
            <p class="feed-desc">"${ticket.descricao}"</p>
            <div class="feed-meta">
                <span>📁 ${ticket.categoria}</span>
            </div>
        `;
        feedDiv.appendChild(card);
    });
}

function getPriorityColor(priority) {
    const p = priority.toLowerCase();
    if (p.includes('baixa')) return '#4caf50'; // Green
    if (p.includes('média') || p.includes('media')) return '#ff9800'; // Orange
    if (p.includes('alta')) return '#f44336'; // Red
    if (p.includes('crítica') || p.includes('critica')) return '#9c27b0'; // Purple
    return '#9e9e9e'; // Grey
}
