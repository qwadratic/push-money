from api.models import db, base_models

if __name__ == '__main__':
    from wsgi import app
    with app.app_context():
        db.database.evolve(ignore_tables=base_models)
