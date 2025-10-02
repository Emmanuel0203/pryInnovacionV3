from flask_login import UserMixin
from datetime import datetime

class Usuario(UserMixin):
    def __init__(self, id_usuario, email, password, is_active=True, is_staff=False, last_login=None):
        self.id_usuario = id_usuario
        self.email = email
        self.password = password
        self.is_active_flag = is_active
        self.is_staff = is_staff
        self.last_login = last_login or datetime.utcnow()

    # Flask-Login necesita un id único
    def get_id(self):
        return str(self.id_usuario)

    # Flask-Login requiere estos métodos:
    def is_active(self):
        return self.is_active_flag

    def is_authenticated(self):
        return True  # Se marca True cuando login_user(self) es llamado

    def is_anonymous(self):
        return False
