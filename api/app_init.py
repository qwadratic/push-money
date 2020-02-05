from flask import Flask

from api.core import bp_api
from api.root import bp_root
from api.sharing import bp_sharing

blueprints = [
    bp_api,
    bp_root,
    bp_sharing
]


def app_init():
    app = Flask(__name__)
    for bp in blueprints:
        app.register_blueprint(bp)
    return app
