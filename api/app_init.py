from flask import Flask

from api.core import bp_api
from api.root import bp_root


def app_init():
    app = Flask(__name__)

    @app.after_request
    def handle_global_response(response):
        response.headers.extend({
            'Access-Control-Allow-Origin': '*',
        })
        return response
    app.register_blueprint(bp_api)
    app.register_blueprint(bp_root)
    return app
