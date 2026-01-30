from peewee import Model, CharField, TextField, ForeignKeyField, JSONField
from datalayer.db_config import db
from datalayer.models.tb_user import User

class Table(Model):
    name = CharField(unique=True)
    descricao = TextField()
    dono = ForeignKeyField(User, backref='tables', on_delete='CASCADE')
    players = JSONField(null=True)

    css=TextField(null=True)

    def __str__(self):
        return self.name

    class Meta:
        database = db