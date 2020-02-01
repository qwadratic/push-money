from peewee import SqliteDatabase, Model, CharField, TextField

from config import SQLITE_DBNAME

database = SqliteDatabase(SQLITE_DBNAME)


class BaseModel(Model):
    class Meta:
        database = database


class Wallet(BaseModel):
    link_id = CharField()
    address = CharField()
    mnemonic = TextField()


def create_tables():
    with database:
        database.create_tables([Wallet])
