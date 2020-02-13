from flask import Flask, jsonify, render_template
from flask_swagger import swagger

from api.core import bp_api
from api.sharing import bp_sharing
from api.webhooks import bp_webhooks
from helpers.misc import setup_logging

blueprints = [
    bp_api,
    bp_sharing,
    bp_webhooks
]


def app_init():
    setup_logging()
    app = Flask(__name__)
    for bp in blueprints:
        app.register_blueprint(bp)

    @app.route('/swagger.json')
    def spec():
        swag = swagger(app, from_file_keyword='swagger')
        swag['info']['version'] = "1.0"
        swag['info']['title'] = "Push Money API"
        swag['host'] = "push.money"
        return jsonify(swag)

    @app.route('/swagger')
    def swag():
        return render_template('swagger.html')

    return app
