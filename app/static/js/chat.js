document.addEventListener('DOMContentLoaded', () => {
    const chatContainer = document.getElementById('chat-container');
    const chatWindow = document.getElementById('chat-window');
    const chatForm = document.getElementById('chat-form');
    const messageInput = document.getElementById('message-input');

    // Pega os dados do HTML (passados pelo Flask/Jinja2)
    const tableId = chatContainer.dataset.tableId;
    const currentUserId = chatContainer.dataset.userId;
    const currentUserNickname = chatContainer.dataset.nickname;

    const socket = io(); // Conecta ao servidor WebSocket

    // Rola para o final do chat ao carregar
    chatWindow.scrollTop = chatWindow.scrollHeight;

    // Evento de conexão com o servidor
    socket.on('connect', function() {
        console.log('Conectado ao servidor Socket.IO');
        // Ao conectar, o cliente se junta à sala da mesa
        socket.emit('join', { table_id: tableId, nickname: currentUserNickname });
    });

    // Ouve por novas ações vindas do servidor
    socket.on('receive_action', function(data) {
        const item = document.createElement('li');
        let content = '';

        if (data.action_type === 'chat') {
            content = `<span class="chat-message">${data.details.message}</span>`;
        } else if (data.action_type === 'dice_roll') {
            content = `<span class="dice-roll">rolou ${data.details.dice} e obteve ${data.details.result}</span>`;
        } else {
            content = `<span class="status-message">Ação: ${data.action_type} - ${JSON.stringify(data.details)}</span>`;
        }

        item.innerHTML = `<span class="message-timestamp">[${data.timestamp}]</span> <span class="message-author">${data.author_nickname}:</span> ${content}`;
        chatWindow.appendChild(item);
        chatWindow.scrollTop = chatWindow.scrollHeight; // Auto-scroll
    });

    // Envia uma ação quando o formulário é submetido
    chatForm.addEventListener('submit', function(e) {
        e.preventDefault();
        const message = messageInput.value.trim();

        if (message) {
            let action = {
                user_id: currentUserId,
                table_id: tableId,
                action_type: 'chat',
                details: { message: message }
            };

            if (message.startsWith('/roll')) {
                const parts = message.split(' ');
                const dice = parts[1] || '1d20';
                let result = 0;
                // Simulação básica de rolagem de dados (permite NdX ou dX)
                const diceRegex = /^(\d+)?d(\d+)$/i;
                if (dice.match(diceRegex)) {
                    const match = dice.match(diceRegex);
                    const num_dice = parseInt(match[1]) || 1;
                    const max_val = parseInt(match[2]);
                    for (let i = 0; i < num_dice; i++) {
                        result += Math.floor(Math.random() * max_val) + 1;
                    }
                } else {
                    result = Math.floor(Math.random() * 20) + 1; // Fallback para 1d20
                }
                
                action.action_type = 'dice_roll';
                action.details = { dice: dice, result: result };
            }
            
            socket.emit('send_action', action);
            messageInput.value = '';
        }
    });
});