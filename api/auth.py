import logging

from flask import Blueprint, request, after_this_request, redirect, current_app, jsonify, url_for, g
from flask_login import current_user, login_required
from flask_security import login_user
from flask_security.decorators import anonymous_user_required
from flask_security.utils import config_value
from social_core.actions import do_complete, do_auth, do_disconnect
from social_flask.utils import psa
from werkzeug.local import LocalProxy

bp_auth = Blueprint('auth', __name__, url_prefix='/auth')

security = LocalProxy(lambda: current_app.extensions['security'])
datastore = LocalProxy(lambda: security.datastore)


def do_login(backend, user, social_user):
    name = backend.strategy.setting('REMEMBER_SESSION_NAME', 'keep')
    remember = backend.strategy.session_get(name) or \
               request.cookies.get(name) or \
               request.args.get(name) or \
               request.form.get(name) or \
               False
    security.datastore.add_role_to_user(user, 'user')
    security.datastore.remove_role_from_user(user, 'anonymous')
    return login_user(user, remember=remember)


def _commit(response=None):
    datastore.commit()
    return response


def _ctx(endpoint):
    return security._run_ctx_processor(endpoint)


@bp_auth.route('/login', methods=['GET'])
@bp_auth.route('/login/<string:backend>/', methods=('GET', 'POST'))
@anonymous_user_required
@psa('auth.complete')
def login(backend):
    return do_auth(g.backend)


@bp_auth.route('/complete/<string:backend>/', methods=('GET', 'POST'))
@psa('auth.complete')
def complete(backend, *args, **kwargs):
    return do_complete(g.backend, login=do_login, user=current_user, *args, **kwargs)


@bp_auth.route('/disconnect/<string:backend>/', methods=('POST',))
@bp_auth.route('/disconnect/<string:backend>/<int:association_id>/', methods=('POST',))
@bp_auth.route('/disconnect/<string:backend>/<string:association_id>/', methods=('POST',))
@login_required
@psa()
def disconnect(backend, association_id=None):
    return do_disconnect(g.backend, g.user, association_id)


@bp_auth.route('/admin-login', methods=['GET', 'POST'], endpoint='admin_login')
@anonymous_user_required
def admin_login():
    form_class = security.login_form
    form = form_class(request.form)
    if form.validate_on_submit():
        login_user(form.user, remember=form.remember.data)
        after_this_request(_commit)
        return redirect(form.next.data or url_for('admin.index'))

    return security.render_template(
        config_value('LOGIN_USER_TEMPLATE'), login_user_form=form, **_ctx('login'))
