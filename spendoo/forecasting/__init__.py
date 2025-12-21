from flask import Blueprint

bp = Blueprint('forecasting', __name__)

from . import routes  # noqa: E402,F401
