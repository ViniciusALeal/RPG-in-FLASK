import eventlet # Import eventlet para suporte assíncrono
eventlet.monkey_patch() # Aplica o monkey patch no início

from flask import Flask, render_template, request, redirect, url_for, flash
from flask_socketio import SocketIO, emit, join_room, leave_room
from datalayer.db_config import db
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from datalayer.models.tb_user import User
from datalayer.models.tb_tables import Table
from datalayer.models.tb_action_log import ActionLog
from datalayer.models.tb_table_player import TablePlayer
import datetime

# --- Configuração Inicial do Flask e SocketIO ---
app = Flask(__name__)
app.config['SECRET_KEY'] = 'seu-segredo-super-secreto!' # MUDE ISSO PARA UMA CHAVE SEGURA EM PRODUÇÃO!
# Configura o SocketIO para usar o eventlet como modo assíncrono
socketio = SocketIO(app, async_mode='eventlet')

# --- Configuração do Flask-Login ---
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login' # Redireciona para /login se o usuário não estiver autenticado
login_manager.login_message = "Você precisa estar logado para acessar esta página."
login_manager.login_message_category = "info"

@login_manager.user_loader
def load_user(user_id):
    """Carrega o usuário para o Flask-Login."""
    try:
        return User.get_by_id(int(user_id))
    except User.DoesNotExist:
        return None

# --- Gerenciamento de Conexão com o Banco de Dados ---
@app.before_request
def before_request_handler():
    """Conecta ao banco de dados antes de cada requisição HTTP."""
    db.connect(reuse_if_open=True)

@app.after_request
def after_request_handler(response):
    """Fecha a conexão com o banco de dados após cada requisição HTTP."""
    if not db.is_closed():
        db.close()
    return response


# --- Funções de Exemplo para Preparar o Banco de Dados ---
# Em um aplicativo real, a criação de usuários e mesas seria feita através de rotas de registro/criação.
def setup_database():
    """Conecta ao DB e cria tabelas e dados de exemplo se não existirem."""
    db.connect(reuse_if_open=True)
    db.create_tables([User, Table, ActionLog, TablePlayer], safe=True)
    
    # Cria usuários com senha hasheada se não existirem
    mestre, created_mestre = User.get_or_create(nickname='Mestre')
    if created_mestre:
        mestre.set_password('123')
        mestre.save()

    jogador1, created_jogador1 = User.get_or_create(nickname='Jogador1')
    if created_jogador1:
        jogador1.set_password('456')
        jogador1.save()

    jogador2, created_jogador2 = User.get_or_create(nickname='Jogador2')
    if created_jogador2:
        jogador2.set_password('789')
        jogador2.save()
    
    # Pega o usuário mestre para associar à mesa
    user_mestre = User.get(User.nickname == 'Mestre')
    
    table_caverna, _ = Table.get_or_create(name='A Caverna do Dragão', defaults={'descricao': 'Uma aventura clássica.', 'dono': user_mestre})
    table_floresta, _ = Table.get_or_create(name='Floresta Sombria', defaults={'descricao': 'Mistérios na floresta.', 'dono': user_mestre})
    
    # --- Adiciona jogadores às mesas para exemplo ---
    user_jogador1 = User.get(User.nickname == 'Jogador1')
    user_jogador2 = User.get(User.nickname == 'Jogador2')

    # Adiciona Jogador1 e Jogador2 à mesa "A Caverna do Dragão"
    TablePlayer.get_or_create(user=user_jogador1, table=table_caverna)
    TablePlayer.get_or_create(user=user_jogador2, table=table_caverna)

    # Adiciona apenas Jogador1 à mesa "Floresta Sombria"
    TablePlayer.get_or_create(user=user_jogador1, table=table_floresta)
    
    db.close()

# --- Rotas HTTP ---
@app.route('/')
def index():
    """Página inicial que lista as mesas disponíveis."""
    tables = Table.select()
    return render_template('index.html', tables=tables)

@app.route('/login', methods=['GET', 'POST'])
def login():
    """Página de login."""
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    
    if request.method == 'POST':
        nickname = request.form.get('nickname')
        password = request.form.get('password')
        remember = True if request.form.get('remember') else False

        try:
            user = User.get(User.nickname == nickname)
            if user.check_password(password):
                login_user(user, remember=remember)
                # Redireciona para a página que o usuário tentou acessar ou para o index
                next_page = request.args.get('next')
                return redirect(next_page or url_for('index'))
            else:
                flash('Nickname ou senha inválidos.', 'danger')
        except User.DoesNotExist:
            flash('Nickname ou senha inválidos.', 'danger')
            
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    """Faz o logout do usuário."""
    logout_user()
    return redirect(url_for('index'))

@app.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    """Página de perfil do usuário para ver mesas e alterar dados."""
    if request.method == 'POST':
        new_password = request.form.get('new_password')
        confirm_password = request.form.get('confirm_password')

        # Apenas atualiza a senha se o campo não estiver em branco
        if new_password:
            if new_password != confirm_password:
                flash('As senhas não conferem.', 'danger')
                return redirect(url_for('profile'))
            
            if len(new_password) < 3:
                flash('A nova senha deve ter pelo menos 3 caracteres.', 'danger')
                return redirect(url_for('profile'))

            current_user.set_password(new_password)
            current_user.save()
            flash('Sua senha foi atualizada com sucesso!', 'success')
        else:
            flash('Nenhum dado foi alterado.', 'info')

        return redirect(url_for('profile'))

    # Mesas que o usuário é dono
    owned_tables = Table.select().where(Table.dono == current_user)

    # Mesas que o usuário joga (usando a tabela de associação)
    played_tables = (Table
                     .select()
                     .join(TablePlayer)
                     .where(TablePlayer.user == current_user))

    return render_template('profile.html', user=current_user, owned_tables=owned_tables, played_tables=played_tables)

@app.route('/chat/<int:table_id>')
@login_required
def chat_room(table_id):
    """
    Renderiza a página do chat para uma mesa específica.
    Esta rota é acessada via HTTP para carregar a interface inicial do chat.
    """
    # A autenticação e obtenção do usuário agora são feitas pelo Flask-Login (current_user)
    # TODO: Implementar verificação de permissão (se o usuário logado pode acessar esta 'table_id').
    
    try:
        current_table = Table.get_by_id(table_id)

        # Carrega o histórico de ações (chat e rolagens de dado) para a mesa
        history = (ActionLog
                   .select(ActionLog, User)
                   .join(User)
                   .where(ActionLog.table == current_table)
                   .order_by(ActionLog.timestamp))
        
        return render_template('chat.html', 
                               table_id=table_id, 
                               table_name=current_table.name,
                               custom_css=current_table.css,
                               current_user_id=current_user.id,
                               current_user_nickname=current_user.nickname,
                               history=history)
    except Table.DoesNotExist:
        return "Mesa não encontrada", 404

# --- Eventos do WebSocket (Flask-SocketIO) ---

@socketio.on('connect')
def handle_connect():
    """Chamado quando um cliente WebSocket se conecta."""
    print(f'Cliente conectado: {request.sid}')

@socketio.on('disconnect')
def handle_disconnect():
    """Chamado quando um cliente WebSocket se desconecta."""
    print(f'Cliente desconectado: {request.sid}')

@socketio.on('join')
def on_join(data):
    """
    Permite que um cliente entre em uma sala de chat específica (associada a uma mesa).
    Isso é crucial para que as mensagens sejam enviadas apenas para os participantes daquela mesa.
    """
    table_id = data.get('table_id')
    nickname = data.get('nickname', 'Um usuário')
    if table_id:
        room = f'table_{table_id}'
        join_room(room)
        print(f'Cliente {request.sid} ({nickname}) entrou na sala {room}')
        # Opcional: emitir uma mensagem de "fulano entrou" para a sala
        # emit('status_message', {'msg': f'{nickname} entrou na sala.'}, room=room)

@socketio.on('leave')
def on_leave(data):
    """Permite que um cliente saia de uma sala de chat específica."""
    table_id = data.get('table_id')
    nickname = data.get('nickname', 'Um usuário')
    if table_id:
        room = f'table_{table_id}'
        leave_room(room)
        print(f'Cliente {request.sid} ({nickname}) saiu da sala {room}')
        # Opcional: emitir uma mensagem de "fulano saiu" para a sala
        # emit('status_message', {'msg': f'{nickname} saiu da sala.'}, room=room)

@socketio.on('send_action')
def handle_send_action(data):
    """
    Recebe uma ação (chat, rolagem de dado, etc.) do cliente,
    salva no banco de dados e distribui para todos os clientes na mesma sala (mesa).
    """
    action_type = data.get('action_type')
    details = data.get('details')
    user_id = data.get('user_id') 
    table_id = data.get('table_id')
    
    # Validação básica dos dados recebidos
    if not all([action_type, details, user_id, table_id]):
        print(f"Dados incompletos para send_action: {data}")
        return

    room = f'table_{table_id}' # Define a sala para onde a mensagem será enviada

    db.connect(reuse_if_open=True)
    try:
        user = User.get_by_id(user_id)
        table = Table.get_by_id(table_id)

        if not user or not table:
            print(f"Usuário ou Mesa não encontrados para user_id={user_id}, table_id={table_id}")
            return

        # Cria e salva a entrada no log de ações
        log_entry = ActionLog.create(author=user, table=table, action_type=action_type, details=details)

        # Prepara os dados para enviar de volta aos clientes
        response_data = {'author_id': user.id, 'author_nickname': user.nickname, 'action_type': action_type, 'details': details, 'timestamp': log_entry.timestamp.strftime('%H:%M:%S')}

        # Emite o evento 'receive_action' para TODOS os clientes na sala correta
        emit('receive_action', response_data, room=room)

    except Exception as e:
        print(f"ERRO ao processar ação: {e}")
    finally:
        if not db.is_closed():
            db.close()

# --- Execução do Aplicativo ---
if __name__ == '__main__':
    setup_database() # Garante que o DB e dados de exemplo estejam prontos
    # Inicia o servidor Flask-SocketIO. O host='0.0.0.0' permite acesso de outras máquinas na rede local.
    socketio.run(app, host='0.0.0.0', port=5000, debug=True)