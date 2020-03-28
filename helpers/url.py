from flask import url_for

from api.models import db


def make_icon_url(icon_type, name):
    return db._app.config['BASE_URL'] + url_for('upload.icons', content_type=icon_type, object_name=name)
