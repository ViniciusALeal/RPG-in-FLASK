import datetime
from peewee import Model, CharField, DateTimeField, ForeignKeyField, JSONField
from datalayer.db_config import db
from datalayer.models.tb_user import User
from datalayer.models.tb_tables import Table

class ActionLog(Model):
    """Representa uma única ação (log) ocorrida em uma mesa."""

    # O tipo de ação: 'chat', 'dice_roll', 'status_change', etc.
    action_type = CharField(index=True)

    # Dados específicos da ação, em formato JSON.
    # Ex: {'message': 'Olá'} ou {'dice': '1d20', 'result': 15}
    details = JSONField()

    timestamp = DateTimeField(default=datetime.datetime.now, index=True)

    author = ForeignKeyField(User, backref='actions', on_delete='CASCADE')
    table = ForeignKeyField(Table, backref='actions', on_delete='CASCADE')

    class Meta:
        database = db