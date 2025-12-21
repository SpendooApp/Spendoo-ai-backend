from . import bp
from flask import current_app, jsonify


@bp.route('/')
def index():
    # preserve behavior from the original single-file app
    return 'Hello World!'


@bp.route('/health', methods=['GET'])
def health():
    return jsonify(status='ok')
