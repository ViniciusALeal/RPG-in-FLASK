from peewee import *
from datalayer.db_config import db
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin

class User(Model, UserMixin):
    nickname = CharField(unique=True)
    password_hash = CharField()

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    class Meta:
        database = db