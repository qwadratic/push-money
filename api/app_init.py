from flask import Flask, jsonify, render_template
from flask_swagger import swagger
from flask_uploads import configure_uploads, patch_request_class

from api.core import bp_api
from api.customization import bp_customization
from api.sharing import bp_sharing
from api.upload import bp_upload, images
from api.webhooks import bp_webhooks
from config import DEV
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

    app.config['BASE_URL'] = 'https://push.money{}'.format('/dev' if DEV else '')
    app.config['UPLOADED_IMAGES_DEST'] = 'content/user_images'
    app.config['UPLOADED_IMAGES_URL'] = app.config['BASE_URL'] + '/api/upload/'
    configure_uploads(app, images)
    patch_request_class(app)

    @app.route('/swagger.json')
    def spec():
        swag = swagger(app, from_file_keyword='swagger')
        swag['info']['version'] = "1.0"
        swag['info']['title'] = "Push Money API"
        swag['tags'] = [
            {
                "name": "core",
                "description": "API for push wallet core functionality and spending"
            },
            {
                "name": "sharing",
                "description": "API for multipush creation and distribution"
            },
            {
                "name": "customization",
                "description": "API for customized push wallet creation"
            },
        ]
        swag['host'] = "push.money"
        swag['basePath'] = "/dev"
        return jsonify(swag)

    @app.route('/swagger')
    def swag():
        return render_template('swagger.html')

    return app
