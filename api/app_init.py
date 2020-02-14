from flask import Flask, jsonify, render_template, url_for, abort, redirect, request
from flask_admin.contrib.peewee import ModelView
from flask_login import current_user
from flask_security import PeeweeUserDatastore, Security
from flask_security.utils import encrypt_password, hash_password, get_identity_attributes
from flask_swagger import swagger
from flask_uploads import configure_uploads
from flask_admin import Admin, helpers as admin_helpers

from api.core import bp_api
from api.customization import bp_customization
from api.models import PushWallet, User, Role, UserRole
from api.sharing import bp_sharing
from api.upload import bp_upload, images
from api.webhooks import bp_webhooks
from config import ADMIN_PASS, SECURITY_PASSWORD_SALT, APP_SECRET_KEY
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

    app.config['SECRET_KEY'] = APP_SECRET_KEY
    app.config['SECURITY_PASSWORD_HASH'] = "pbkdf2_sha512"
    app.config['SECURITY_PASSWORD_SALT'] = SECURITY_PASSWORD_SALT
    app.config['MAX_CONTENT_LENGTH'] = 10 * 1024 * 1024  # 10 MB
    app.config['UPLOADED_IMAGES_DEST'] = 'user_images'
    app.config['UPLOADED_IMAGES_URL'] = '/dev/api/upload/'
    configure_uploads(app, images)

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
            from peewee import fn as peeweeFn
            try:
                return self.user_model.get(self.user_model.id == identifier)
            except self.user_model.DoesNotExist:
                pass
            for attr in get_identity_attributes():
                column = getattr(self.user_model, attr)
                try:
                    return self.user_model.get(
                        peeweeFn.Lower(column) == peeweeFn.Lower(identifier))
                except self.user_model.DoesNotExist:
                    pass

        def add_role_to_user(self, user, role):
            user, role = self._prepare_role_modify_args(user.email, role.name)
            result = self.UserRole.select().where(
                self.UserRole.user == user.id,
                self.UserRole.role == role.id,
            )
            if result.count():
                return False
            else:
                self.put(self.UserRole.create(user=user.id, role=role.id))
                return True
    user_datastore = UserDatastore(None, User, Role, UserRole)
    security = Security(app, user_datastore)

    admin = Admin(app, name='pushmoney', template_mode='bootstrap3')
    admin.add_view(SecureModelView(PushWallet))
    # admin.add_view(ModelView(Post, db.session))

    @security.context_processor
    def security_context_processor():
        return dict(
            admin_base_template=admin.base_template,
            admin_view=admin.index_view,
            h=admin_helpers,
            get_url=url_for)

    with app.app_context():
        super_role, _ = Role.get_or_create(name='superuser')
        user_role, _ = Role.get_or_create(name='user')
        user_datastore.create_user(
            first_name='Admin',
            email='admin',
            password=hash_password(ADMIN_PASS),
            roles=[user_role, super_role])

    return app
