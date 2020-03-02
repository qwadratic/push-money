from base64 import b64decode

from flask import Blueprint, jsonify, request, current_app, send_from_directory, make_response
from flask_uploads import UploadSet, IMAGES
from http import HTTPStatus
from api.models import UserImage
from providers.giftery import GifteryAPIClient

bp_upload = Blueprint('upload', __name__, url_prefix='/api')
images = UploadSet('IMAGES', IMAGES)


@bp_upload.route('/upload', methods=['POST'])
def upload_img():
    """
    swagger: swagger/customization/upload-img.yml
    """
    if 'img' not in request.files:
        return jsonify({'error': 'No image provided'}), HTTPStatus.BAD_REQUEST

    filename = images.save(request.files['img'])
    image = UserImage.create(filename=filename, url=images.url(filename))
    return jsonify({'url': image.url, 'id': image.id})


@bp_upload.route('/upload/<path:filename>')
def get_uploaded_img(filename):
    """
    swagger: swagger/customization/upload-img-get.yml
    """
    config = current_app.upload_set_config.get('IMAGES')
    return send_from_directory('../' + config.destination, filename)


@bp_upload.route('/content/icons/<string:content_type>-<string:object_name>', endpoint='icons')
def get_category_icon(content_type, object_name):
    ext = '' if content_type == 'shop' else '.png'
    return send_from_directory('../content', f'{content_type}/{object_name}{ext}')


@bp_upload.route('/content/giftery/<int:order_id>', endpoint='giftery-pdf')
def get_giftery_pdf(order_id):
    client = GifteryAPIClient()
    pdf_base64 = client.get_certificate(order_id)
    pdf = b64decode(pdf_base64)
    response = make_response(pdf)
    response.headers['Content-Disposition'] = f"attachment; filename=giftery-{order_id}.pdf"
    response.mimetype = 'application/pdf'
    return response
