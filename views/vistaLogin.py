# views/login.py - ADAPTADO A response["datos"]
from flask import Blueprint, render_template, request, redirect, url_for, flash, session, current_app
import os
from forms.formsLogin import LoginForm
from flask_login import login_user, login_required
from models.Usuario import Usuario
from utils.api_client import APIClient
import requests
from utils.authorization import ensure_user_roles_loaded

login_bp = Blueprint("login", __name__, template_folder="templates")

@login_bp.route("/login", methods=["GET", "POST"])
def login_view():
    form = LoginForm()
    if form.validate_on_submit():
        email = form.email.data.lower() if form.email.data else form.email.data
        password = form.password.data
        # Usar APIClient para autenticación contra /api/Autenticacion/token
        try:
            client = APIClient('usuario')
            # El endpoint de tu API espera la contraseña en texto plano y devuelve un JWT en 'token'
            auth = client.authenticate(email, password, tabla='usuario', campoUsuario='email', campoContrasena='password', use_hash=False)
            if not auth or not isinstance(auth, dict) or not auth.get('token'):
                # Puede contener detalles en auth['raw'] si se desea loggear
                flash('Credenciales inválidas o error en autenticación', 'danger')
            else:
                token = auth.get('token')
                expiracion = auth.get('expiracion')

                # login en Flask-Login (creamos un objeto Usuario mínimo)
                usuario = Usuario(
                    email=email,
                    password='[PROTECTED]',
                    is_active=True,
                    is_staff=False,
                    last_login=None
                )
                login_user(usuario, remember=True)

                # Guardar token, expiración y email en la sesión (token raw sin 'Bearer ')
                session['api_token'] = token
                if expiracion:
                    session['api_token_expires'] = expiracion
                session['user_email'] = email
                # Log minimal info for debugging (mask token)
                try:
                    masked = (str(token)[:8] + '...') if len(str(token)) > 12 else str(token)
                except Exception:
                    masked = '<unavailable>'
                current_app.logger.info('Usuario autenticado y token guardado en sesión (masked=%s)', masked)

                # Intentar obtener roles del usuario inmediatamente y guardarlos en sesión
                try:
                    from utils.authorization import ensure_user_roles_loaded
                    # Clear any previously cached roles for this session so we always reload
                    session.pop('user_roles', None)
                    session.pop('is_admin', None)
                    ensure_user_roles_loaded()
                except Exception:
                    current_app.logger.exception('No se pudieron cargar roles tras el login')

                # No exponer el token al cliente: mantenemos el token solo en server-side session
                flash('¡Login exitoso! Bienvenido', 'success')
                return redirect(url_for('main.menu'))
        except Exception as e:
            current_app.logger.exception('Error durante autenticación')
            flash(f'Error inesperado: {e}', 'danger')

    return render_template("login.html", form=form)


@login_bp.route('/logout')
def logout():
    # Borrar token y limpiar sesión
    session.pop('api_token', None)
    session.pop('api_token_expires', None)
    session.pop('user_email', None)
    session.clear()
    flash('Has cerrado sesión correctamente', 'success')
    return redirect(url_for('login.login_view'))


# 🧪 Ruta de prueba para ver estructura real de usuarios
@login_bp.route('/test-users')
def test_users():
    backend_url = os.getenv("BACKEND_LOCAL_URL")
    if not backend_url:
        return "❌ BACKEND_LOCAL_URL no configurada", 500

    try:
        response = requests.get(f"{backend_url}/usuario", timeout=5)
        api_data = response.json()
        users = api_data.get("datos", [])

        # Mostrar estructura de los primeros usuarios (sin contraseñas)
        sample_users = []
        for user in users[:3]:
            safe_user = {k: v for k, v in user.items() if 'password' not in k.lower() and 'contrasena' not in k.lower()}
            sample_users.append(safe_user)

        return f"""
        <h2>📊 Estructura de usuarios (response['datos'])</h2>
        <p><strong>URL:</strong> {backend_url}/usuario</p>
        <p><strong>Total usuarios:</strong> {len(users)}</p>
        <pre>{sample_users}</pre>
        <p><strong>Campos disponibles en el primer usuario:</strong></p>
        <pre>{list(users[0].keys()) if users else 'No hay usuarios'}</pre>
        """
    except Exception as e:
        return f"❌ Error: {e}", 500



@login_bp.route('/debug-roles')
@login_required
def debug_roles():
    """Debug route to inspect role resolution for the current logged user."""
    info = {}
    user_email = session.get('user_email')
    info['session_user_email'] = user_email
    info['session_user_roles'] = session.get('user_roles')
    info['session_is_admin'] = session.get('is_admin')

    # Try perfil lookup
    try:
        from utils.api_client import get_api_client
        perfil_client = get_api_client('perfil')
        perfil_resp = perfil_client.get_by_key('usuario_email', user_email)
        info['perfil_lookup'] = perfil_resp
    except Exception as e:
        info['perfil_lookup_error'] = str(e)

    # Try usuario lookup
    try:
        from utils.api_client import get_api_client
        usuario_client = get_api_client('usuario')
        usuario_resp = usuario_client.get_by_id('email', user_email)
        info['usuario_lookup'] = usuario_resp
    except Exception as e:
        info['usuario_lookup_error'] = str(e)

    # Ensure roles loaded now
    try:
        roles = ensure_user_roles_loaded()
        info['resolved_roles'] = roles
    except Exception as e:
        info['resolved_roles_error'] = str(e)

    # Return a readable HTML page
    from markupsafe import escape
    body = '<h2>Debug roles</h2>'
    body += f"<p><strong>session_user_email:</strong> {escape(str(user_email))}</p>"
    body += f"<p><strong>session_user_roles:</strong> {escape(str(session.get('user_roles')))}</p>"
    body += f"<p><strong>session_is_admin:</strong> {escape(str(session.get('is_admin')))}</p>"
    # Show whether an API token exists in the server-side session (masked for safety)
    token = session.get('api_token')
    if token:
        masked = (str(token)[:8] + '...') if len(str(token)) > 12 else str(token)
        body += f"<p><strong>api_token_present:</strong> True (masked: {escape(masked)})</p>"
    else:
        body += f"<p><strong>api_token_present:</strong> False</p>"
    body += '<h3>perfil lookup</h3><pre>' + (escape(str(info.get('perfil_lookup'))) or '') + '</pre>'
    body += '<h3>usuario lookup</h3><pre>' + (escape(str(info.get('usuario_lookup'))) or '') + '</pre>'
    body += '<h3>resolved roles</h3><pre>' + (escape(str(info.get('resolved_roles'))) or '') + '</pre>'
    return body



@login_bp.route('/debug-session')
def debug_session():
    """Unprotected helper (dev only) to inspect session state quickly.
    Shows masked api_token presence and session keys. Remove in production.
    """
    from markupsafe import escape
    out = ['<h2>Session dump (dev)</h2>']
    user_email = session.get('user_email')
    out.append(f"<p><strong>user_email:</strong> {escape(str(user_email))}</p>")
    token = session.get('api_token')
    if token:
        masked = (str(token)[:8] + '...') if len(str(token)) > 12 else str(token)
        out.append(f"<p><strong>api_token_present:</strong> True (masked: {escape(masked)})</p>")
    else:
        out.append(f"<p><strong>api_token_present:</strong> False</p>")
    out.append(f"<p><strong>session keys:</strong> {escape(str(list(session.keys())))}</p>")
    out.append(f"<pre>{escape(str({k: (v if k!='api_token' else '***') for k,v in session.items()}))}</pre>")
    return '\n'.join(out)
