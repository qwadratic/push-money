import peeweedbevolve
from passlib.handlers.pbkdf2 import pbkdf2_sha256
from peewee import SqliteDatabase, CharField, TextField, PostgresqlDatabase, Model, IntegerField, ForeignKeyField

from config import SQLITE_DBNAME, LOCAL, DB_USER, DB_NAME

database = SqliteDatabase(SQLITE_DBNAME) if LOCAL \
    else PostgresqlDatabase(DB_NAME, user=DB_USER)


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
        if self.password_hash is None:
            return True
        return password is not None and pbkdf2_sha256.verify(password, self.password_hash)


class PushCampaign(BaseModel):
    sendpulse_addressbook_id = IntegerField(null=True)
    wallet_link_id = CharField()
    cost_pip = CharField()


def create_tables():
    with database:
        database.create_tables([PushWallet, PushCampaign])
