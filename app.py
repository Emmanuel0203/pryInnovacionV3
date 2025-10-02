# app.py
from flask import Flask, render_template, redirect, url_for
from flask_wtf.csrf import CSRFProtect
from dotenv import load_dotenv
from datetime import timedelta
from utils.api_client import APIClient
import os

# 🔑 Extensiones
from extensions import login_manager

# 🔹 Blueprints
from views.vistaLogin import login_bp
from views.vistaIdeas import ideas_bp
from views.vistaOportunidades import oportunidades_bp
from views.vistaSoluciones import soluciones_bp
from views.vistaPerfil import perfil_bp
from views.vistaDashboard import dashboard_bp
from views.vistaMain import main_bp



# Cargar variables de entorno
load_dotenv()

app = Flask(__name__)

    # CSRF
csrf = CSRFProtect(app)

# 🔑 Cargar SECRET_KEY desde variables de entorno
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY")

if not app.config["SECRET_KEY"]:
    raise ValueError("❌ SECRET_KEY no encontrada en las variables de entorno")

    # Inicializar extensiones
login_manager.init_app(app)
login_manager.login_view = "login.login_view"
login_manager.login_message = "Debes iniciar sesión para acceder a esta página."

    # Definir user_loader
from models.Usuario import Usuario

from extensions import login_manager


@login_manager.user_loader
def load_user(user_id):
    client = APIClient("usuario")
    result = client.get_data(where_condition=f"id_usuario = {user_id}")
    if result:
        user_data = result[0]
        return Usuario(
            id_usuario=user_data["id_usuario"],
            email=user_data["email"],
            password=user_data["password"],
            is_active=user_data.get("is_active", True),
            is_staff=user_data.get("is_staff", False),
            last_login=user_data.get("last_login")
        )
    return None



    # Registrar blueprints
app.register_blueprint(login_bp, url_prefix='/login')
app.register_blueprint(ideas_bp, url_prefix='/ideas')
app.register_blueprint(oportunidades_bp, url_prefix='/oportunidades')
app.register_blueprint(soluciones_bp, url_prefix='/soluciones')
app.register_blueprint(perfil_bp, url_prefix='/perfil')
app.register_blueprint(dashboard_bp, url_prefix='/dashboard')
app.register_blueprint(main_bp, url_prefix='/')

    # Rutas raíz / errores
@app.route('/')
def index():
      from flask_login import current_user
      if not current_user.is_authenticated:
        return redirect(url_for('login.login_view'))
      return redirect(url_for('dashboard.index'))

@app.errorhandler(404)
def page_not_found(e):
    return render_template('error/404.html'), 404

@app.errorhandler(500)
def internal_server_error(e):
    return render_template('error/500.html'), 500




# =========================
# Arranque de la app
# =========================
if __name__ == '__main__':
    app.run(debug=True, port=5001)
