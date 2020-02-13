from flask import Flask, jsonify, render_template
from flask_swagger import swagger
from flask_uploads import configure_uploads

from api.core import bp_api
from api.customization import bp_customization
from api.sharing import bp_sharing
from api.upload import bp_upload, images
from api.webhooks import bp_webhooks
from helpers.misc import setup_logging

blueprints = [
    bp_api,
    bp_sharing,
    bp_webhooks,
    bp_upload,
    bp_customization
]


def app_init():
    setup_logging()
    app = Flask(__name__)
    for bp in blueprints:
        app.register_blueprint(bp)

    app.config['MAX_CONTENT_LENGTH'] = 10 * 1024 * 1024  # 10 MB
    app.config['UPLOADED_IMAGES_DEST'] = 'user_images'
    app.config['UPLOADED_IMAGES_URL'] = '/api/upload/'
    configure_uploads(app, images)

    @app.route('/swagger.json')
    def spec():
        swag = swagger(app, from_file_keyword='swagger')
        swag['info']['version'] = "1.0"
        swag['info']['title'] = "Push Money API"
        swag['tags'] = [
            "1. Core - API for push wallet core functionality and spending",
            "2. Sharing - API for multipush creation and distribution",
            "3. Customization - API for customized push wallet creation"
        ]
        swag['host'] = "push.money"
        swag['basePath'] = "/dev"
        return jsonify(swag)

    @app.route('/swagger')
    def swag():
        return render_template('swagger.html')

    return app
