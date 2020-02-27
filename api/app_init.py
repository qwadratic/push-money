from logging import info

from flask import Flask, url_for, abort, redirect, request, g, logging
from flask_admin.contrib.peewee import ModelView
from flask_admin.menu import MenuLink
from flask_login import current_user
from flask_security import PeeweeUserDatastore, Security
from flask_security.utils import hash_password, get_identity_attributes, login_user
from flask_uploads import configure_uploads, patch_request_class
from flask_admin import Admin, helpers as admin_helpers
from peewee import fn
from social_flask.routes import social_auth
from social_flask_peewee.models import init_social

from api.auth import bp_auth
from api.core import bp_api
from api.customization import bp_customization
from api.models import db, PushWallet, User, Role, UserRole, PushCampaign, OrderHistory, WebhookEvent, Recipient, \
    UserImage, CustomizationSetting
from api.sharing import bp_sharing
from api.surprise import bp_surprise
from api.swagger import bp_swagger
from api.upload import bp_upload, images
from api.webhooks import bp_webhooks
from config import ADMIN_PASS, FlaskConfig
from helpers.misc import setup_logging

blueprints = [
    bp_auth,
    social_auth,
    bp_api,
    bp_sharing,
    bp_webhooks,
    bp_upload,
    bp_customization,
    bp_surprise,
    bp_swagger
]


def app_init():
    setup_logging()
    app = Flask(__name__)
    app.config.from_object(FlaskConfig)
    for bp in blueprints:
        app.register_blueprint(bp)

    configure_uploads(app, images)
    patch_request_class(app)
    db.init_app(app)

    # Flask-Security setup

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

    init_social(app, db.database)
    user_datastore = UserDatastore(db, User, Role, UserRole)
    security = Security(app, user_datastore)
    security.login_manager.login_view = 'auth.login'

    @app.before_request
    def anonymous_login():
        # if current_user.get_id() is not None:
        #     return
        # anonymous_role, _ = Role.get_or_create(name='anonymous')
        # u = user_datastore.create_user(roles=[anonymous_role])
        # login_user(u)
        g.user = current_user

    @app.context_processor
    def inject_user():
        try:
            return {'user': g.user}
        except AttributeError:
            return {'user': None}

    # @app.errorhandler(500)
    # def error_handler(error):
    #     if isinstance(error, SocialAuthBaseException):
    #         return redirect('/socialerror')

    # Flask-Admin setup

    class SecureModelView(ModelView):
        def is_accessible(self):
            return current_user.is_active and \
                   current_user.is_authenticated and \
                   current_user.has_role('superuser')

        def _handle_view(self, name, **kwargs):
            if not self.is_accessible():
                if current_user.is_authenticated:
                    abort(403)
                return redirect(url_for('auth.admin_login', next=request.url))

    class AuthenticatedMenuLink(MenuLink):

        def is_accessible(self):
            return current_user.is_authenticated

    admin = Admin(app, name='pushmoney', template_mode='bootstrap3')
    admin.add_view(SecureModelView(User))
    admin.add_view(SecureModelView(PushWallet))
    admin.add_view(SecureModelView(PushCampaign))
    admin.add_view(SecureModelView(OrderHistory))
    admin.add_view(SecureModelView(WebhookEvent))
    admin.add_view(SecureModelView(Recipient))
    admin.add_view(SecureModelView(UserImage))
    admin.add_view(SecureModelView(CustomizationSetting))
    admin.add_link(AuthenticatedMenuLink(name='Logout', endpoint='security.logout'))

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

    endpoints = sorted([
        str(rule) for rule in app.url_map.iter_rules()
        if 'admin' not in str(rule)])
    info('\n'.join(endpoints))
    return app
