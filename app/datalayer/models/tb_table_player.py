from peewee import *
from datalayer.db_config import db
from .tb_user import User
from .tb_tables import Table

class TablePlayer(Model):
    """Tabela de associação (Many-to-Many) entre User e Table para representar os jogadores."""
    user = ForeignKeyField(User, backref='played_tables')
    table = ForeignKeyField(Table, backref='players')

    class Meta:
        database = db
        # Garante que um usuário só pode ser jogador de uma mesa uma vez
        primary_key = CompositeKey('user', 'table')