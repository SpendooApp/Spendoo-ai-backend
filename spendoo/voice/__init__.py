from flask import Blueprint

bp = Blueprint('voice', __name__)

from . import routes  # noqa: E402,F401
