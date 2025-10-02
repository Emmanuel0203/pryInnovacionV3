# extensions.py
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager

# Instancias de las extensiones
db = SQLAlchemy()
login_manager = LoginManager()

# Configuración del clogin
login_manager.login_view = "login.login_view"
login_manager.login_message = "Por favor inicia sesión para acceder a esta página."

# user_loader se configurará en app.py o en models, según prefieras