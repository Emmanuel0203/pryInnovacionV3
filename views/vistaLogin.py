# views/login.py - ADAPTADO A response["datos"]
from flask import Blueprint, render_template, request, redirect, url_for, flash, session
import requests
import os
from forms.formsLogin import LoginForm
from flask_login import login_user
from models.Usuario import Usuario

login_bp = Blueprint("login", __name__, template_folder="templates")

@login_bp.route("/login", methods=["GET", "POST"])
def login_view():
    form = LoginForm()
    if form.validate_on_submit():
        email = form.email.data.lower() if form.email.data else form.email.data
        password = form.password.data

        backend_url = os.getenv("BACKEND_LOCAL_URL")  # Ej: http://localhost:5186/api
        if not backend_url:
            flash("Error de configuración del sistema", "danger")
            return render_template("templatesLogin/login.html", form=form)

        try:
            # 📌 Ahora tu API devuelve algo así:
            # {
            #   "mensaje": "OK",
            #   "datos": [ { ...usuario1... }, { ...usuario2... } ]
            # }
            search_url = f"{backend_url}/usuario"
            response = requests.get(search_url, timeout=10)

            if response.status_code == 200:
                api_data = response.json()

                # Extraer la lista de usuarios desde "datos"
                users = api_data.get("datos", [])
                print(f"👥 Total usuarios en response['datos']: {len(users)}")

                # Buscar usuario por email (ignorando mayúsculas/minúsculas)
                user_found = None
                for user in users:
                    if user.get("email") and user.get("email").lower() == email:
                        user_found = user
                        break

                if user_found:
                    print(f"👤 Usuario encontrado: {user_found}")

                    # Comparar contraseña
                    stored_password = user_found.get("password") or user_found.get("contrasena")
                    if stored_password == password:
                        usuario = Usuario(
                            email=user_found.get("email"),
                            password=user_found.get("password"),
                            is_active=user_found.get("is_active", True),
                            is_staff=user_found.get("is_staff", False),
                            last_login=user_found.get("last_login")
                        )

                        login_user(usuario, remember=True)  # 👈 Aquí lo guarda Flask-Login
                        # Guardar email en la sesión para compatibilidad con vistas existentes
                        session['user_email'] = usuario.email
                        flash("¡Login exitoso! Bienvenido", "success")
                        return render_template("menu.html")
                    else:
                        flash("Contraseña incorrecta", "danger")
                else:
                    flash("Usuario no encontrado", "danger")
            else:
                flash(f"Error del servidor: {response.status_code}", "danger")

        except requests.exceptions.ConnectionError:
            flash("No se puede conectar al servidor. Verifica que la API esté ejecutándose.", "danger")
        except requests.exceptions.Timeout:
            flash("La conexión tardó demasiado tiempo", "danger")
        except Exception as e:
            flash(f"Error inesperado: {e}", "danger")

    return render_template("login.html", form=form)


@login_bp.route('/logout')
def logout():
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
