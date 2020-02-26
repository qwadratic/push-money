import logging

from flask import Blueprint, request, after_this_request, redirect, current_app, jsonify, url_for
from flask_login import current_user
from flask_security import login_user
from flask_security.decorators import anonymous_user_required
from flask_security.utils import config_value
from werkzeug.local import LocalProxy

from http import HTTPStatus

bp_auth = Blueprint('auth', __name__, url_prefix='/auth')

security = LocalProxy(lambda: current_app.extensions['security'])
datastore = LocalProxy(lambda: security.datastore)


def _commit(response=None):
    datastore.commit()
    return response


def _ctx(endpoint):
    return security._run_ctx_processor(endpoint)


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


@bp_auth.route('/login', methods=['GET', 'POST'], endpoint='login')
@anonymous_user_required
def login():
    logging.info(current_user)
    if request.method == 'GET':
        return jsonify({'error': 'No login form'}), HTTPStatus.BAD_REQUEST
    return 'hello'
