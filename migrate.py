from api.models import database


if __name__ == '__main__':
    database.evolve(ignore_tables=['basemodel', 'passwordprotectedmodel'])
