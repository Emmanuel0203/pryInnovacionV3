from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app
from forms.formsRegistro import RegisterForm
from datetime import datetime
from utils.api_client import APIClient, get_api_client
from utils.procedimientos import crear_usuario_con_roles
import json

register_bp = Blueprint('register', __name__)

@register_bp.route('/register', methods=['GET', 'POST'])
def register_view():
    form = RegisterForm()

    # Load perfil/roles choices from backend so SelectField has choices before validation
    try:
        rol_client = get_api_client('rol')
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
        else:
            # Fallback: ensure SelectField has at least one choice so validation
            # doesn't fail silently if backend is unreachable.
            form.perfil.choices = [("1", "Usuario")]
    except Exception:
        # If roles retrieval fails, leave choices as None and let form validation handle it with user-friendly message
        current_app.logger.exception('No se pudieron cargar los roles para el formulario de registro')
        # Assign a safe default choice so the form can still be enviado en entornos sin el backend
        try:
            form.perfil.choices = [("1", "Usuario")]
        except Exception:
            pass
    
    if request.method == 'POST':
        current_app.logger.debug("POST /register recibido: %s", request.form)
        if not form.validate_on_submit():
            # Log and surface validation errors so it's visible why submission did not proceed
            current_app.logger.warning("Validación de formulario fallida: %s", form.errors)
            # Flash each field error for the user
            for field, errors in form.errors.items():
                for err in errors:
                    flash(f"Error en {field}: {err}", "danger")
            return render_template('register.html', form=form)

        # Si la validación pasa, continuar con la lógica existente
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

            # Build perfil payload for the SP so the DB can insert perfil atomically
            # Determine the human-readable role name from the selected roles_list.
            role_name = None
            try:
                first = roles_list[0]
                if isinstance(first, dict):
                    # If caller provided a 'rol' string directly in the role entry, prefer it
                    if 'rol' in first and isinstance(first['rol'], str):
                        role_name = first['rol']
                    # Otherwise try to resolve fkidrol -> name using previously loaded `roles` list
                    elif 'fkidrol' in first:
                        try:
                            rid = int(first['fkidrol'])
                        except Exception:
                            rid = None
                        if rid is not None:
                            try:
                                for r in (roles or []):
                                    r_id = r.get('id') or r.get('codigo') or r.get('fkidrol') or r.get('codigo_rol')
                                    try:
                                        if r_id is not None and int(r_id) == rid:
                                            role_name = r.get('nombre') or r.get('descripcion') or r.get('rol_nombre')
                                            break
                                    except Exception:
                                        continue
                            except Exception:
                                # roles may be undefined or not iterable; ignore and fallback below
                                pass
                            # Fallback mapping for common ids if lookup failed
                            if not role_name:
                                if rid == 1:
                                    role_name = 'Administrador'
                                elif rid == 2:
                                    role_name = 'Experto'
                                elif rid == 3:
                                    role_name = 'Usuario'
                                else:
                                    role_name = str(rid)
            except Exception:
                role_name = None

            # Final safe default
            if not role_name:
                role_name = 'Usuario'

            perfil_payload = {
                "nombre": form.nombre.data,
                "usuario_email": form.email.data,
                "rol": role_name,
                "fecha_nacimiento": form.fecha_nacimiento.data.strftime('%Y-%m-%d') if form.fecha_nacimiento.data else None,
                "direccion": form.direccion.data,
                "descripcion": form.descripcion.data
            }

            # Call the stored procedure and forward perfil to be inserted atomically
            resp = crear_usuario_con_roles(form.email.data, form.password.data, roles_list, perfil=perfil_payload)
            current_app.logger.debug(f"Respuesta procedimiento crear_usuario_con_roles: {resp}")

            # For frontend testing: show a helpful debug flash with basic result info
            # The ProcedimientosController returns an object like { Procedimiento, Resultados, Total, Mensaje }
            try:
                # Prefer structured feedback
                total = None
                mensaje = None
                if isinstance(resp, dict):
                    total = resp.get('Total') or resp.get('total') or (resp.get('Resultados') and len(resp.get('Resultados')))
                    mensaje = resp.get('Mensaje') or resp.get('mensaje') or resp.get('Mensaje', None)

                if total is not None:
                    flash(f'Respuesta SP: registros procesados = {total}', 'info')
                else:
                    flash('Registro enviado. Ver logs para más detalles.', 'info')

                # Determine success robustly using the computed `total` and possible nested SP JSON
                ok = False
                try:
                    # If we computed total (from resp.get('total') or similar), treat >0 as success
                    if total is not None:
                        try:
                            if int(total) > 0:
                                ok = True
                        except Exception:
                            # non-integer total ignored
                            pass

                    # Some backends return the SP result as a JSON string inside resp['resultados'][0]
                    if not ok and isinstance(resp, dict) and isinstance(resp.get('resultados'), list) and len(resp.get('resultados')) > 0:
                        first = resp['resultados'][0]
                        if isinstance(first, dict):
                            # look for a JSON string value and parse it
                            for v in first.values():
                                if isinstance(v, str):
                                    try:
                                        inner = json.loads(v)
                                        if isinstance(inner, dict) and inner.get('status') in ('ok', 'success'):
                                            ok = True
                                            break
                                    except Exception:
                                        # not JSON, continue
                                        pass

                    # As a final fallback, check top-level status key
                    if not ok and isinstance(resp, dict) and resp.get('status') in ('ok', 'success'):
                        ok = True
                except Exception:
                    current_app.logger.exception('Error evaluando la respuesta del SP')

                if ok:
                    flash('Usuario registrado exitosamente. Por favor inicia sesión.', 'success')
                    return redirect(url_for('login.login_view'))
                else:
                    # If SP reported success but frontend didn't detect it before, show a different notice
                    flash('No se pudo crear el usuario. Contacte al administrador.', 'danger')
                    return render_template('register.html', form=form)
            except Exception:
                # Fallback simple behavior
                flash('Resultado inesperado al crear usuario; ver logs.', 'warning')
                return render_template('register.html', form=form)
                
        except Exception as e:
            current_app.logger.exception('Error durante el registro')
            flash(f'Error durante el registro: {str(e)}', 'danger')
    
    return render_template('register.html', form=form)