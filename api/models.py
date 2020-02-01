from passlib.handlers.pbkdf2 import pbkdf2_sha256
from peewee import SqliteDatabase, Model, CharField, TextField

from config import SQLITE_DBNAME

database = SqliteDatabase(SQLITE_DBNAME)


class BaseModel(Model):
    class Meta:
        database = database


class PushWallet(BaseModel):
    link_id = CharField()
    address = CharField()
    mnemonic = TextField()
    sender = TextField()
    recipient = TextField()
    password_hash = TextField()

    def auth(self, password):
        return pbkdf2_sha256.verify(password, self.password_hash)


def create_tables():
    with database:
        database.create_tables([PushWallet])
