from flask import Blueprint, render_template

bp_dev = Blueprint('dev', __name__, template_folder='templates/dev')


@bp_dev.route('/')
def index():
    return render_template('index.html')
