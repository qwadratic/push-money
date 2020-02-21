from flask import Flask, jsonify, render_template, url_for, abort, redirect, request
from flask_admin.contrib.peewee import ModelView
from flask_login import current_user
from flask_security import PeeweeUserDatastore, Security
from flask_security.utils import hash_password, get_identity_attributes
from flask_swagger import swagger
from flask_uploads import configure_uploads, patch_request_class
from flask_admin import Admin, helpers as admin_helpers
from peewee import fn

from api.core import bp_api
from api.customization import bp_customization
from api.models import db, PushWallet, User, Role, UserRole, PushCampaign, OrderHistory, WebhookEvent, Recipient, \
    UserImage, CustomizationSetting
from api.sharing import bp_sharing
from api.surprise import bp_surprise
from api.upload import bp_upload, images
from api.webhooks import bp_webhooks
from config import DEV, ADMIN_PASS, SECURITY_PASSWORD_SALT, APP_SECRET_KEY, APP_DATABASE
from helpers.misc import setup_logging

blueprints = [
    bp_api,
    bp_sharing,
    bp_webhooks,
    bp_upload,
    bp_customization,
    bp_surprise
]


def app_init():
    setup_logging()
    app = Flask(__name__)
    for bp in blueprints:
        app.register_blueprint(bp)

    app.config['FLASK_ADMIN_SWATCH'] = 'cyborg'

    app.config['DATABASE'] = APP_DATABASE
    app.config['BASE_URL'] = 'https://push.money{}'.format('/dev' if DEV else '')
    app.config['UPLOADED_IMAGES_DEST'] = 'content/user_images'
    app.config['UPLOADED_IMAGES_URL'] = app.config['BASE_URL'] + '/api/upload/'

    app.config['SECRET_KEY'] = APP_SECRET_KEY
    app.config['SECURITY_PASSWORD_HASH'] = "pbkdf2_sha512"
    app.config['SECURITY_PASSWORD_SALT'] = SECURITY_PASSWORD_SALT
    app.config['SECURITY_LOGIN_URL'] = '/login/'
    app.config['SECURITY_LOGOUT_URL'] = '/logout/'
    app.config['SECURITY_POST_LOGIN_VIEW'] = '/admin/'
    app.config['SECURITY_POST_LOGOUT_VIEW'] = '/admin/'

    configure_uploads(app, images)
    patch_request_class(app)
    db.init_app(app)

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

    class SecureModelView(ModelView):
        def is_accessible(self):
            return current_user.is_active and \
                current_user.is_authenticated and \
                current_user.has_role('superuser')

        def _handle_view(self, name, **kwargs):
            """
            Override builtin _handle_view in order to redirect users when a view is not accessible.
            """
            if not self.is_accessible():
                if current_user.is_authenticated:
                    # permission denied
                    abort(403)
                else:
                    # login
                    return redirect(url_for('security.login', next=request.url))

    class UserDatastore(PeeweeUserDatastore):
        def get_user(self, identifier):
            if isinstance(identifier, int):
                try:
                    return self.user_model.get(self.user_model.id == identifier)
                except self.user_model.DoesNotExist:
                    pass
            for attr in get_identity_attributes():
                column = getattr(self.user_model, attr)
                try:
                    return self.user_model.get(
                        fn.Lower(column) == fn.Lower(identifier))
                except self.user_model.DoesNotExist:
                    pass

    user_datastore = UserDatastore(db, User, Role, UserRole)
    security = Security(app, user_datastore)

    admin = Admin(app, name='pushmoney', template_mode='bootstrap3')
    admin.add_view(SecureModelView(User))
    admin.add_view(SecureModelView(PushWallet))
    admin.add_view(SecureModelView(PushCampaign))
    admin.add_view(SecureModelView(OrderHistory))
    admin.add_view(SecureModelView(WebhookEvent))
    admin.add_view(SecureModelView(Recipient))
    admin.add_view(SecureModelView(UserImage))
    admin.add_view(SecureModelView(CustomizationSetting))

    @security.context_processor
    def security_context_processor():
        return dict(
            admin_base_template=admin.base_template,
            admin_view=admin.index_view,
            h=admin_helpers,
            get_url=url_for)

    @app.before_first_request
    def create_admin():
        if User.get_or_none(email='admin'):
            db.close_db(None)
            return
        super_role, _ = Role.get_or_create(name='superuser')
        user_role, _ = Role.get_or_create(name='user')
        user_datastore.create_user(
            first_name='Admin',
            email='admin',
            password=hash_password(ADMIN_PASS),
            roles=[user_role, super_role])
        db.close_db(None)
    return app
