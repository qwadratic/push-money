from api.models import db


if __name__ == '__main__':
    from wsgi import app
    with app.app_context():
        db.database.evolve(ignore_tables=[
            'basemodel', 'passwordprotectedmodel', 'peeweeassociationmixin',
            'peeweenoncemixin', 'peeweecodemixin', 'peeweeusermixin',
            'peeweepartialmixin'])
