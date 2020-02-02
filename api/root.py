from flask import Blueprint, render_template

bp_root = Blueprint('root', __name__, url_prefix='/')


@bp_root.route('/', methods=['GET'])
def readme():
    return render_template('guide.html')
