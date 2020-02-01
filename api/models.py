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
    sender = TextField(null=True)
    recipient = TextField(null=True)
    password_hash = TextField(null=True)

    def auth(self, password):
        if password is None and self.password_hash is not None:
            return False
        return pbkdf2_sha256.verify(password, self.password_hash)


def create_tables():
    with database:
        database.create_tables([PushWallet])
