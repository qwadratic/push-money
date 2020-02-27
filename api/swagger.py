from flask import Blueprint, current_app, jsonify, render_template
from flask_swagger import swagger

bp_swagger = Blueprint('swagger', __name__)


@bp_swagger.route('/swagger')
def swag():
    return render_template('swagger.html')


@bp_swagger.route('/swagger.json')
def spec():
    swag = swagger(current_app, from_file_keyword='swagger')
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
    swag['host'] = "dev.push.money"
    return jsonify(swag)

