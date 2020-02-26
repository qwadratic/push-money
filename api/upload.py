from flask import Blueprint, jsonify, request, current_app, send_from_directory
from flask_uploads import UploadSet, IMAGES
from http import HTTPStatus
from api.models import UserImage

bp_upload = Blueprint('upload', __name__, url_prefix='/api/upload')
images = UploadSet('IMAGES', IMAGES)


@bp_upload.route('', methods=['POST'])
def upload_img():
    """
    swagger: swagger/customization/upload-img.yml
    """
    if 'img' not in request.files:
        return jsonify({'error': 'No image provided'}), HTTPStatus.BAD_REQUEST

    filename = images.save(request.files['img'])
    image = UserImage.create(filename=filename, url=images.url(filename))
    return jsonify({'url': image.url, 'id': image.id})


@bp_upload.route('/<path:filename>')
def get_uploaded_img(filename):
    """
    swagger: swagger/customization/upload-img-get.yml
    """
    config = current_app.upload_set_config.get('IMAGES')
    return send_from_directory('../' + config.destination, filename)
