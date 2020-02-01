import os

from api.models import create_tables
from config import SQLITE_DBNAME


if __name__ == '__main__':
    os.remove(SQLITE_DBNAME)
    create_tables()
