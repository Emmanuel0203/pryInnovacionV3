import os
from pathlib import Path

# Directorio base del proyecto
BASE_DIR = Path(__file__).resolve().parent

# =========================
# Configuración de Flask
# =========================
FLASK_CONFIG = {
    'SECRET_KEY': os.environ.get('SECRET_KEY', 'dev'),
    'DEBUG': os.environ.get('FLASK_DEBUG', 'True').lower() == 'true',
    'SESSION_COOKIE_SECURE': False,
    'SESSION_COOKIE_HTTPONLY': True,
    'PERMANENT_SESSION_LIFETIME': 3600  # 1 hora
}

SECRET_KEY = FLASK_CONFIG['SECRET_KEY']
DEBUG = FLASK_CONFIG['DEBUG']

# =========================
# Configuración API externa
# =========================
API_CONFIG = {
    'base_url': os.environ.get('API_BASE_URL', 'http://localhost:5186/api'),
    'timeout': 30,
    'headers': {
        'Content-Type': 'application/json',
        'Accept': 'application/json',
        # Puedes añadir un token si tu API lo requiere
        # 'Authorization': f"Bearer {os.environ.get('API_TOKEN', '')}"
    }
}

# =========================
# Archivos estáticos y media
# =========================
STATIC_URL = '/static/'
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')
STATICFILES_DIRS = [os.path.join(BASE_DIR, 'static')]

MEDIA_URL = '/media/'
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')

UPLOAD_FOLDER = os.path.join(BASE_DIR, 'uploads')
MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16 MB

# =========================
# Configuración de sesión
# =========================
SESSION_TYPE = 'filesystem'
LANGUAGE_CODE = 'es'
TIME_ZONE = 'UTC'

# =========================
# Configuración de autenticación
# =========================
LOGIN_URL = '/login'
LOGIN_REDIRECT_URL = '/dashboard'
LOGOUT_REDIRECT_URL = '/login'

WTF_CSRF_ENABLED = True
WTF_CSRF_SECRET_KEY = SECRET_KEY

# =========================
# Configuración de correo
# =========================
MAIL_SERVER = os.environ.get('MAIL_SERVER', 'smtp.example.com')
MAIL_PORT = int(os.environ.get('MAIL_PORT', 587))
MAIL_USE_TLS = os.environ.get('MAIL_USE_TLS', 'True').lower() == 'true'
MAIL_USERNAME = os.environ.get('MAIL_USERNAME', 'user@example.com')
MAIL_PASSWORD = os.environ.get('MAIL_PASSWORD', 'password')
MAIL_DEFAULT_SENDER = os.environ.get('MAIL_DEFAULT_SENDER', 'noreply@example.com')

# =========================
# Clases de Configuración
# =========================
class Config:
    SECRET_KEY = SECRET_KEY
    UPLOAD_FOLDER = UPLOAD_FOLDER
    MAX_CONTENT_LENGTH = MAX_CONTENT_LENGTH
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'pdf', 'doc', 'docx'}

class DevelopmentConfig(Config):
    DEBUG = True
    TESTING = False

class TestingConfig(Config):
    DEBUG = False
    TESTING = True

class ProductionConfig(Config):
    DEBUG = False
    TESTING = False

config = {
    'development': DevelopmentConfig,
    'testing': TestingConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig
}
