from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app
from forms.formsRegistro import RegisterForm
from datetime import datetime
from utils.api_client import APIClient
from utils.procedimientos import crear_usuario_con_roles
import json

register_bp = Blueprint('register', __name__)

@register_bp.route('/register', methods=['GET', 'POST'])
def register_view():
    form = RegisterForm()

    # Load perfil/roles choices from backend so SelectField has choices before validation
    try:
        rol_client = APIClient('rol')
        roles = rol_client.get_data()
        # roles expected as list of dicts with keys like 'id' or 'codigo' and 'nombre' or 'descripcion'
        choices = []
        for r in roles:
            # Try common id fields
            rid = r.get('id') or r.get('codigo') or r.get('fkidrol') or r.get('codigo_rol')
            name = r.get('nombre') or r.get('descripcion') or r.get('rol_nombre') or str(rid)
            if rid is not None:
                choices.append((str(rid), name))
        if choices:
            form.perfil.choices = choices
    except Exception:
        # If roles retrieval fails, leave choices as None and let form validation handle it with user-friendly message
        current_app.logger.exception('No se pudieron cargar los roles para el formulario de registro')
    
    if request.method == 'POST' and form.validate_on_submit():
        try:
            # Determine roles_list from form.perfil
            roles_list = []
            try:
                # If perfil is an id
                role_id = int(form.perfil.data)
                roles_list = [{"fkidrol": role_id, "fkidaplicacion": 1}]
            except Exception:
                try:
                    parsed = json.loads(form.perfil.data)
                    if isinstance(parsed, dict) and 'fkidrol' in parsed:
                        roles_list = [parsed]
                    elif isinstance(parsed, list):
                        roles_list = parsed
                except Exception:
                    roles_list = []

            if not roles_list:
                flash('Formato de perfil/roles inválido. Contacte al administrador.', 'danger')
                return render_template('register.html', form=form)

            # Use helper to call the stored procedure (it will request server-side hashing)
            resp = crear_usuario_con_roles(form.email.data, form.password.data, roles_list)
            current_app.logger.debug(f"Respuesta procedimiento crear_usuario_con_roles: {resp}")

            # If we reach here, the user creation succeeded (SP either inserted or skipped existing)
            # Now create/insert perfil record via API
            perfil_client = APIClient("perfil")
            perfil_payload = {
                "nombre": form.nombre.data,
                "usuario_email": form.email.data,
                "rol": "Usuario",
                "fecha_nacimiento": form.fecha_nacimiento.data.strftime('%Y-%m-%d') if form.fecha_nacimiento.data else None,
                "direccion": form.direccion.data,
                "descripcion": form.descripcion.data,
                "area_expertise": form.area_expertise.data,
                "info_adicional": form.informacion_adicional.data if hasattr(form, 'informacion_adicional') else form.informacion_adicional.data
            }

            perfil_resp = perfil_client.insert_data(perfil_payload)
            current_app.logger.debug(f"Respuesta creación perfil: {perfil_resp}")

            if perfil_resp and (perfil_resp.get('status_code') == 201 or perfil_resp.get('estado') == 200 or perfil_resp.get('estado') == 201):
                flash('Usuario registrado exitosamente. Por favor inicia sesión.', 'success')
                return redirect(url_for('login.login_view'))
            else:
                # Inform user but do not attempt complex rollback here
                flash('Usuario creado pero no se pudo crear el perfil. Contacte al administrador.', 'warning')
                return redirect(url_for('login.login_view'))
                
        except Exception as e:
            current_app.logger.exception('Error durante el registro')
            flash(f'Error durante el registro: {str(e)}', 'danger')
    
    return render_template('register.html', form=form)