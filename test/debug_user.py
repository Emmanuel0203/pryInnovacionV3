from flask_login import current_user
from flask import Blueprint

debug_bp = Blueprint("debug", __name__)

@debug_bp.route("/debug_user")
def debug_user():
    if current_user.is_authenticated:
        return f"Usuario autenticado: {current_user.get_id()}"
    else:
        return "No hay usuario autenticado"
