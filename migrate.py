import os

from api.models import create_tables
from config import SQLITE_DBNAME


if __name__ == '__main__':
    os.rename(SQLITE_DBNAME, SQLITE_DBNAME + '.bak')
    create_tables()
