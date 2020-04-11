from datetime import datetime
from functools import partial
from http import HTTPStatus
from logging import info

from flask import Flask, url_for, abort, redirect, request, g, logging, after_this_request, jsonify
from flask_admin.contrib.peewee import ModelView
from flask_admin.menu import MenuLink
from flask_login import current_user, user_logged_out
from flask_security import PeeweeUserDatastore, Security, AnonymousUser
from flask_security.utils import hash_password, get_identity_attributes, login_user
from flask_uploads import configure_uploads, patch_request_class
from flask_admin import Admin, helpers as admin_helpers
from peewee import fn
from social_core.exceptions import SocialAuthBaseException
from social_flask.routes import social_auth
from social_flask_peewee.models import init_social
from werkzeug.middleware.proxy_fix import ProxyFix

from api.auth import bp_auth
from api.core import bp_api
from api.customization import bp_customization
from api.dev import bp_dev
from api.merchant import bp_merchant
from api.models import db, PushWallet, User, Role, UserRole, PushCampaign, OrderHistory, WebhookEvent, Recipient, \
    UserImage, CustomizationSetting, Product, Category, Shop
from api.rewards import bp_rewards
from api.sharing import bp_sharing
# from api.surprise import bp_surprise
from api.swagger import bp_swagger
from api.upload import bp_upload, images
from api.webhooks import bp_webhooks
from config import ADMIN_PASS, FlaskConfig, DEV
from helpers.misc import setup_logging

blueprints = [
    bp_auth,
    bp_api,
    bp_sharing,
    bp_webhooks,
    bp_upload,
    bp_customization,
    bp_swagger,
    bp_rewards,
    # social_auth,
    # bp_surprise,
    # bp_merchant,
]
if DEV:
    blueprints.append(bp_dev)

class ReverseProxied(object):
    def __init__(self, app):
        self.app = app

    def __call__(self, environ, start_response):
        scheme = environ.get('HTTP_X_FORWARDED_PROTO')
        if scheme:
            environ['wsgi.url_scheme'] = scheme
        return self.app(environ, start_response)


def app_init():
    setup_logging()
    app = Flask(__name__)
    app.wsgi_app = ReverseProxied(app.wsgi_app)
    app.wsgi_app = ProxyFix(app.wsgi_app, num_proxies=2)
    app.config.from_object(FlaskConfig)
    for bp in blueprints:
        app.register_blueprint(bp)

    configure_uploads(app, images)
    patch_request_class(app)
    db.init_app(app)

    # Flask-Security setup

    class UserDatastore(PeeweeUserDatastore):

        def login_user_silent(self, user):
            login_user(user)
            user.login_count -= 1
            self.put(user)

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

    @security.login_manager.unauthorized_handler
    def unauthorized():
        return 'Unauthorized', HTTPStatus.UNAUTHORIZED

    @user_logged_out.connect_via(app)
    def on_logout(*args, **kwargs):
        user = kwargs['user']
        if user.has_role('superuser'):
            return
        user_datastore.add_role_to_user(user, 'anonymous')
        user_datastore.remove_role_from_user(user, 'user')
        user_datastore.login_user_silent(user)

    @app.before_request
    def login_implicitly():
        if isinstance(current_user._get_current_object(), AnonymousUser):
            u = user_datastore.create_user(roles=['anonymous'])
            user_datastore.login_user_silent(u)
        g.user = current_user

    @app.context_processor
    def inject_user():
        try:
            return {'user': g.user}
        except AttributeError:
            return {'user': None}

    if not DEV:
        @app.errorhandler(500)
        def error_handler(error):
            if isinstance(error, SocialAuthBaseException):
                return redirect('/socialerror')

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
    admin.add_view(SecureModelView(Shop))
    admin.add_view(SecureModelView(Category))
    admin.add_view(SecureModelView(Product))
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
        anonymous_role, _ = Role.get_or_create(name='anonymous')
        super_role, _ = Role.get_or_create(name='superuser')
        user_role, _ = Role.get_or_create(name='user')
        user_datastore.create_user(
            first_name='Admin',
            email='admin',
            password=hash_password(ADMIN_PASS),
            confirmed_at=datetime.utcnow(),
            roles=[user_role, super_role])
        db.close_db(None)

    endpoints = sorted([
        str(rule) for rule in app.url_map.iter_rules()
        if 'admin' not in str(rule)])
    info('\n'.join(endpoints))
    return app
