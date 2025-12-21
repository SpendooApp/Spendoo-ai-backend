from . import bp
from flask import jsonify


@bp.route('/', methods=['GET'])
def info():
    return jsonify(module='chatbot', status='ok')


@bp.route('/health', methods=['GET'])
def health():
    return jsonify(status='ok')

