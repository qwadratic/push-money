import os

from api.models import create_tables, database, BaseModel
from config import SQLITE_DBNAME, LOCAL


def local():
    if os.path.isfile(SQLITE_DBNAME):
        os.rename(SQLITE_DBNAME, SQLITE_DBNAME + '.bak')
    create_tables()


def prod():
    database.evolve(ignore_tables=[BaseModel])


if __name__ == '__main__':
    local() if LOCAL else prod()
