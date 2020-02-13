from flask import Blueprint, request, jsonify

from api.consts import HTTP_404_NOT_FOUND
from api.models import CustomizationSetting, UserImage
from api.upload import images

bp_customization = Blueprint('customization', __name__, url_prefix='/api/custom')


@bp_customization.route('/create-setting', methods=['POST'])
def create_customization_setting():
    """
    swagger: swagger/customization/customization-create.yml
    """
    payload = request.get_json() or {}

    setting_fields = [
        'logo_image_id', 'head_text', 'background_name', 'animation_name',
        'animation_text', 'target_shop', 'email_image_id', 'email_text'
    ]
    settings = {
        f: payload.get(f) for f in setting_fields
    }

    customization_obj = CustomizationSetting.create(**settings)
    return jsonify({'id': customization_obj.id})


@bp_customization.route('/get-setting/<int:setting_id>', methods=['GET'])
def get_customization_setting(setting_id):
    """
    swagger: swagger/customization/customization-get.yml
    """
    customization_obj = CustomizationSetting.get_or_none(id=setting_id)
    if not customization_obj:
        return jsonify({'error': 'Customization setting not found'}), HTTP_404_NOT_FOUND

    response = {}
    if customization_obj.logo_image_id:
        logo_img = UserImage.get_or_none(id=customization_obj.logo_image_id)
        if not logo_img:
            return jsonify({'error': 'Logo image not found'}), HTTP_404_NOT_FOUND
        response['logo_image_url'] = images.url(logo_img.filename)

    if customization_obj.email_image_id:
        email_img = UserImage.get_or_none(id=customization_obj.email_image_id)
        if not email_img:
            return jsonify({'error': 'Logo image not found'}), HTTP_404_NOT_FOUND
        response['email_image_url'] = images.url(email_img.filename)

    setting_fields = [
        'head_text', 'background_name', 'animation_name',
        'animation_text', 'target_shop', 'email_text'
    ]
    response.update({f: getattr(customization_obj, f, None) for f in setting_fields})
    return jsonify(response)
