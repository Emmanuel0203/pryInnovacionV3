from flask import (
    Blueprint, render_template, request, redirect, url_for, flash, session, current_app
)
from flask_login import login_required
from utils.api_client import APIClient
from forms.formsOportunidades import OportunidadForm
from datetime import datetime
import os
from werkzeug.utils import secure_filename


oportunidades_bp = Blueprint(
    "vistaOportunidad",
    __name__,
    template_folder="templates",
    url_prefix="/oportunidades"
)

oportunidad_client = APIClient("oportunidad")

@oportunidades_bp.route("/", methods=["GET"])
@login_required
def list_oportunidades():
    try:
        # Capturar parámetros de filtro de la URL
        selected_tipo = request.args.get('tipo_innovacion', '', type=str)
        selected_foco = request.args.get('foco_innovacion', '', type=str)
        selected_estado = request.args.get('estado', '', type=str)
        
        current_app.logger.debug(f"Filtros aplicados - Tipo: {selected_tipo}, Foco: {selected_foco}, Estado: {selected_estado}")
        oportunidades = oportunidad_client.get_all()
        # Log de la respuesta cruda para depuración
        current_app.logger.debug(f"Oportunidades raw (desde API): {oportunidades}")

        focos_tipos = {
            "focos": oportunidad_client.fetch_endpoint_data("foco_innovacion"),
            "tipos": oportunidad_client.fetch_endpoint_data("tipo_innovacion")
        }

        # Obtener información de usuarios
        usuario_client = APIClient("usuario")
        usuarios = usuario_client.get_all()

        # Mapear IDs a nombres para foco, tipo de innovación y usuarios
        foco_map = {f['id_foco_innovacion']: f['name'] for f in focos_tipos['focos']}
        tipo_map = {t['id_tipo_innovacion']: t['name'] for t in focos_tipos['tipos']}
        usuario_map = {u.get('id'): f"{u.get('nombre', '')} {u.get('apellido', '')}".strip() for u in usuarios}

        # Agregar nombres a cada oportunidad
        for oportunidad in oportunidades:
            oportunidad['foco_innovacion_nombre'] = foco_map.get(oportunidad.get('id_foco_innovacion'), "Desconocido")
            oportunidad['tipo_innovacion_nombre'] = tipo_map.get(oportunidad.get('id_tipo_innovacion'), "Desconocido")
            # Si creador_por ya contiene email, mantenemos; sino, usamos el mapeo de usuarios
            oportunidad['creador_por_nombre'] = oportunidad.get('creador_por') or usuario_map.get(oportunidad.get('creador_por'), "Usuario desconocido")

        # Aplicar filtros a las oportunidades
        oportunidades_filtradas = []
        for oportunidad in oportunidades:
            # Filtro por tipo de innovación
            if selected_tipo and str(oportunidad.get('id_tipo_innovacion', '')) != selected_tipo:
                continue

            # Filtro por foco de innovación
            if selected_foco and str(oportunidad.get('id_foco_innovacion', '')) != selected_foco:
                continue

            # Filtro por estado
            if selected_estado:
                if selected_estado == 'True' and not oportunidad.get('estado', False):
                    continue
                elif selected_estado == 'False' and oportunidad.get('estado', False):
                    continue

            oportunidades_filtradas.append(oportunidad)

        current_app.logger.debug(f"Oportunidades después de filtros: {len(oportunidades_filtradas)} de {len(oportunidades)}")

        # Configurar las opciones dinámicas en el formulario
        form = OportunidadForm()
        # Añadir opción vacía para "Todos"
        # Ensure choice values are integers to match SelectField(coerce=int)
        form.foco_innovacion.choices = [('', '-- Todos --')] + [(int(f['id_foco_innovacion']), f['name']) for f in focos_tipos['focos']]
        form.tipo_innovacion.choices = [('', '-- Todos --')] + [(int(t['id_tipo_innovacion']), t['name']) for t in focos_tipos['tipos']]

        # Establecer valores seleccionados en el formulario
        if selected_tipo:
            form.tipo_innovacion.data = int(selected_tipo) if selected_tipo.isdigit() else None
        if selected_foco:
            form.foco_innovacion.data = int(selected_foco) if selected_foco.isdigit() else None

        # Verificar que las opciones se asignaron correctamente
        current_app.logger.debug(f"Opciones de foco_innovacion: {form.foco_innovacion.choices}")
        current_app.logger.debug(f"Opciones de tipo_innovacion: {form.tipo_innovacion.choices}")

    except Exception as e:
        current_app.logger.exception("Error al procesar oportunidades")
        flash(f"Error al obtener las oportunidades: {e}", "danger")
        oportunidades_filtradas = []
        selected_tipo = selected_foco = selected_estado = ''
        form = OportunidadForm()
        form.foco_innovacion.choices = [('', '-- Todos --')]
        form.tipo_innovacion.choices = [('', '-- Todos --')]

    current_app.logger.debug(f"Datos de oportunidades: {oportunidades_filtradas}")

    return render_template("list_oportunidades.html", 
                         oportunidades=oportunidades_filtradas, 
                         form=form, 
                         selected_tipo=selected_tipo,
                         selected_foco=selected_foco,
                         selected_estado=selected_estado)

@oportunidades_bp.route("/create", methods=["GET", "POST"])
@login_required
def create_oportunidad():
    form = OportunidadForm()

    # Cargar opciones dinámicamente desde la API
    try:
        focos_tipos = {
            "focos": oportunidad_client.fetch_endpoint_data("foco_innovacion"),
            "tipos": oportunidad_client.fetch_endpoint_data("tipo_innovacion")
        }
        # Ensure choice values are integers to match SelectField(coerce=int)
        form.foco_innovacion.choices = [(int(f['id_foco_innovacion']), f['name']) for f in focos_tipos['focos']]
        form.tipo_innovacion.choices = [(int(t['id_tipo_innovacion']), t['name']) for t in focos_tipos['tipos']]
        print(f"[DEBUG] Opciones cargadas: Focos: {focos_tipos['focos']}, Tipos: {focos_tipos['tipos']}")
    except Exception as e:
        print("[ERROR] Error al cargar opciones de innovación", e)
        form.foco_innovacion.choices = []
        form.tipo_innovacion.choices = []

    if form.validate_on_submit():
        print("[DEBUG] Formulario válido. Enviando datos a la API...")
        
        # Manejar archivo multimedia y guardar en static/uploads
        archivo_url = None
        archivo = request.files.get('archivo_multimedia')
        if archivo and archivo.filename:
            import os
            from werkzeug.utils import secure_filename
            
            # Crear directorio uploads si no existe
            upload_folder = os.path.join(current_app.root_path, 'static', 'uploads')
            if not os.path.exists(upload_folder):
                os.makedirs(upload_folder)
            
            # Generar nombre seguro y único para el archivo
            filename = secure_filename(archivo.filename)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_")
            unique_filename = f"{timestamp}{filename}"
            file_path = os.path.join(upload_folder, unique_filename)
            
            try:
                archivo.save(file_path)
                # Guardar la URL relativa para la base de datos
                archivo_url = f"uploads/{unique_filename}"
                print(f"[DEBUG] Archivo guardado en: {file_path}, URL: {archivo_url}")
            except Exception as e:
                print(f"[ERROR] Error al guardar archivo: {e}")
                flash("Error al guardar el archivo multimedia", "danger")
                return render_template("create_oportunidades.html", form=form)

        payload = {
            "id_tipo_innovacion": form.tipo_innovacion.data,
            "id_foco_innovacion": form.foco_innovacion.data,
            "titulo": form.titulo.data,
            "descripcion": form.descripcion.data,
            "palabras_claves": form.palabras_claves.data,
            "recursos_requeridos": form.recursos_requeridos.data,
            "archivo_multimedia": archivo_url or "",  # URL del archivo o cadena vacía
            # fecha_creacion es requerida por la BD (no nula). Generarla en el backend con la fecha actual.
            "fecha_creacion": datetime.now().strftime("%Y-%m-%d"),
            "creador_por": session.get("user_email", ""),  # Email del usuario de la sesión
            "estado": False  # Por defecto False según la tabla
        }

        # Validar que los campos obligatorios estén presentes y cumplan con los requisitos
        if not payload.get("id_tipo_innovacion") or not payload.get("id_foco_innovacion"):
            print("[ERROR] Los campos 'id_tipo_innovacion' y 'id_foco_innovacion' son obligatorios.")
            flash("Error: Los campos 'Tipo de Innovación' y 'Foco de Innovación' son obligatorios.", "danger")
            return render_template("create_oportunidades.html", form=form)

        if not payload.get("titulo") or len(payload["titulo"]) > 200:
            print("[ERROR] El campo 'titulo' es obligatorio y no debe exceder 200 caracteres.")
            flash("Error: El título es obligatorio y no debe exceder 200 caracteres.", "danger")
            return render_template("create_oportunidades.html", form=form)

        if not payload.get("descripcion") or len(payload["descripcion"]) > 250:
            print("[ERROR] El campo 'descripcion' es obligatorio y no debe exceder 250 caracteres.")
            flash("Error: La descripción es obligatoria y no debe exceder 250 caracteres.", "danger")
            return render_template("create_oportunidades.html", form=form)

        if not payload.get("palabras_claves") or len(payload["palabras_claves"]) > 200:
            print("[ERROR] El campo 'palabras_claves' es obligatorio y no debe exceder 200 caracteres.")
            flash("Error: Las palabras clave son obligatorias y no deben exceder 200 caracteres.", "danger")
            return render_template("create_oportunidades.html", form=form)

        # Validar que el archivo multimedia no exceda la longitud permitida (200 caracteres)
        if payload.get("archivo_multimedia") and len(payload["archivo_multimedia"]) > 200:
            print("[ERROR] La URL del archivo multimedia no debe exceder 200 caracteres.")
            flash("Error: El nombre del archivo multimedia es demasiado largo.", "danger")
            return render_template("create_oportunidades.html", form=form)

        # Validar que el creador no exceda 50 caracteres
        if payload.get("creador_por") and len(payload["creador_por"]) > 50:
            print("[ERROR] El campo 'creador_por' no debe exceder 50 caracteres.")
            flash("Error: El email del creador es demasiado largo.", "danger")
            return render_template("create_oportunidades.html", form=form)

        # Asegurarse de enviar el payload como un objeto JSON
        current_app.logger.debug(f"[DEBUG] Payload preparado para enviar: {payload}")
        current_app.logger.debug(f"[DEBUG] Enviando solicitud POST a {oportunidad_client.base_url}/oportunidad")
        current_app.logger.debug(f"[DEBUG] Headers utilizados: {{'Content-Type': 'application/json'}}")

        response = oportunidad_client.insert_data(payload)  # Enviar el objeto JSON directamente

        # Log detallado de la respuesta de la API
        if response:
            current_app.logger.debug(f"[DEBUG] Respuesta completa de la API: {response}")
            if 'content' in response:
                current_app.logger.debug(f"[DEBUG] Contenido de la respuesta: {response['content']}")
        else:
            current_app.logger.error("[ERROR] No se recibió respuesta de la API")

        # Implementar Post/Redirect/Get para evitar reenvío del formulario
        if response and response.get("status_code") == 201:
            current_app.logger.info("Redirigiendo a la lista de oportunidades después de creación exitosa.")
            flash("Oportunidad creada exitosamente.", "success")
            return redirect(url_for("vistaOportunidad.list_oportunidades"))

        # En caso de error, mostrar mensaje y mantener el formulario
        error_message = response.get("mensaje", "Error desconocido") if response else "Sin respuesta del API"
        current_app.logger.error(f"Error al crear la oportunidad: {error_message}")
        flash(f"Error al crear la oportunidad: {error_message}", "danger")

    # Si no se valida el formulario, renderizar nuevamente con errores
    return render_template("create_oportunidades.html", form=form)

@oportunidades_bp.route("/update/<int:codigo_oportunidad>", methods=["GET", "POST"])
@login_required
def update_oportunidad(codigo_oportunidad):
    oportunidad = oportunidad_client.get_by_key("codigo_oportunidad", codigo_oportunidad)
    if not oportunidad:
        flash("Oportunidad no encontrada", "error")
        return redirect(url_for("vistaOportunidad.list_oportunidades"))

    try:
        focos_tipos = {
            "focos": oportunidad_client.fetch_endpoint_data("foco_innovacion"),
            "tipos": oportunidad_client.fetch_endpoint_data("tipo_innovacion")
        }
    except Exception as e:
        current_app.logger.exception("Error al cargar opciones dinámicas")
        focos_tipos = {
            "focos": [],
            "tipos": []
        }

    # Crear el formulario, asignar choices primero y luego aplicar los datos
    form = OportunidadForm()
    # Ensure the underlying values are ints so WTForms coerce=int can match them
    form.foco_innovacion.choices = [(int(f['id_foco_innovacion']), f['name']) for f in focos_tipos['focos']]
    form.tipo_innovacion.choices = [(int(t['id_tipo_innovacion']), t['name']) for t in focos_tipos['tipos']]
    # Debug: log what we received and what choices were created
    current_app.logger.debug(f"focos_tipos (raw): {focos_tipos}")
    current_app.logger.debug(f"tipo_innovacion.choices: {form.tipo_innovacion.choices}")
    current_app.logger.debug(f"foco_innovacion.choices: {form.foco_innovacion.choices}")
    # Procesar los datos de la oportunidad una vez que las choices están establecidas
    # Coerce numeric id fields to int so they match SelectField(coerce=int)
    data_to_process = dict(oportunidad[0])
    try:
        if 'id_tipo_innovacion' in data_to_process and data_to_process['id_tipo_innovacion'] is not None:
            data_to_process['id_tipo_innovacion'] = int(data_to_process['id_tipo_innovacion'])
    except Exception:
        pass
    try:
        if 'id_foco_innovacion' in data_to_process and data_to_process['id_foco_innovacion'] is not None:
            data_to_process['id_foco_innovacion'] = int(data_to_process['id_foco_innovacion'])
    except Exception:
        pass

    current_app.logger.debug(f"data_to_process before process: {data_to_process}")
    # Map backend keys to form field names and coerce ids to int
    mapped = dict(data_to_process)
    if 'id_tipo_innovacion' in mapped:
        try:
            mapped['tipo_innovacion'] = int(mapped.get('id_tipo_innovacion'))
        except Exception:
            mapped['tipo_innovacion'] = None
    if 'id_foco_innovacion' in mapped:
        try:
            mapped['foco_innovacion'] = int(mapped.get('id_foco_innovacion'))
        except Exception:
            mapped['foco_innovacion'] = None

    # Only pre-populate the form from the backend on GET; on POST we must let WTForms process request.form
    if request.method != 'POST':
        form.process(data=mapped)
        current_app.logger.debug(f"form.data after process: {form.data}")
    else:
        # On POST, do not override with backend data — let WTForms parse request.form
        current_app.logger.debug("POST request: skipping form.process to allow WTForms to parse request.form")

    if request.method == "POST":
        if form.validate_on_submit():
            # Manejar archivo multimedia en actualización
            archivo_url = oportunidad[0].get("archivo_multimedia", "")  # Mantener el archivo existente por defecto
            archivo = request.files.get('archivo_multimedia')
            
            if archivo and archivo.filename:
                import os
                from werkzeug.utils import secure_filename
                
                # Crear directorio uploads si no existe
                upload_folder = os.path.join(current_app.root_path, 'static', 'uploads')
                if not os.path.exists(upload_folder):
                    os.makedirs(upload_folder)
                
                # Eliminar archivo anterior si existe
                old_file_path = oportunidad[0].get("archivo_multimedia")
                if old_file_path:
                    old_full_path = os.path.join(current_app.root_path, 'static', old_file_path)
                    if os.path.exists(old_full_path):
                        try:
                            os.remove(old_full_path)
                            print(f"[DEBUG] Archivo anterior eliminado: {old_full_path}")
                        except Exception as e:
                            print(f"[WARNING] No se pudo eliminar archivo anterior: {e}")
                
                # Guardar nuevo archivo
                filename = secure_filename(archivo.filename)
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_")
                unique_filename = f"{timestamp}{filename}"
                file_path = os.path.join(upload_folder, unique_filename)
                
                try:
                    archivo.save(file_path)
                    archivo_url = f"uploads/{unique_filename}"
                    print(f"[DEBUG] Nuevo archivo guardado en: {file_path}, URL: {archivo_url}")
                except Exception as e:
                    print(f"[ERROR] Error al guardar archivo: {e}")
                    flash("Error al guardar el archivo multimedia", "danger")
                    return render_template("edit_oportunidades.html", form=form, oportunidad=oportunidad[0])

            payload = {
                "id_tipo_innovacion": form.tipo_innovacion.data,
                "id_foco_innovacion": form.foco_innovacion.data,
                "titulo": form.titulo.data,
                "descripcion": form.descripcion.data,
                "palabras_claves": form.palabras_claves.data,
                "recursos_requeridos": form.recursos_requeridos.data,
                "archivo_multimedia": archivo_url,
                "creador_por": oportunidad[0].get("creador_por"),  # Mantener el creador original
                # use the possibly edited estado from the form
                "estado": form.estado.data if hasattr(form, 'estado') else oportunidad[0].get("estado")
            }

            response = oportunidad_client.update_by_key("codigo_oportunidad", codigo_oportunidad, payload)
            if response and response.get("estado") == 200:
                flash("Oportunidad actualizada correctamente", "success")
                return redirect(url_for("vistaOportunidad.list_oportunidades"))
            else:
                current_app.logger.error(f"Error al actualizar la oportunidad, respuesta API: {response}")
                flash("Error al actualizar la oportunidad", "danger")
        else:
            # Validation failed — log details so we can see which validators blocked the update
            current_app.logger.debug(f"Validación de formulario fallida al actualizar oportunidad {codigo_oportunidad}")
            current_app.logger.debug(f"request.form: {request.form}")
            current_app.logger.debug(f"form.errors: {form.errors}")
            # Also log what WTForms parsed for the select fields and their types
            try:
                current_app.logger.debug(f"form.tipo_innovacion.data: {form.tipo_innovacion.data} (type: {type(form.tipo_innovacion.data)})")
            except Exception:
                current_app.logger.debug("form.tipo_innovacion.data: <unavailable>")
            try:
                current_app.logger.debug(f"form.foco_innovacion.data: {form.foco_innovacion.data} (type: {type(form.foco_innovacion.data)})")
            except Exception:
                current_app.logger.debug("form.foco_innovacion.data: <unavailable>")
            try:
                current_app.logger.debug(f"form.descripcion.data: {form.descripcion.data} (len={len(form.descripcion.data) if form.descripcion.data else 0})")
            except Exception:
                current_app.logger.debug("form.descripcion.data: <unavailable>")
            # Inform the user that validation failed — template already shows per-field errors
            flash("Error al validar el formulario. Revise los campos marcados.", "danger")

    return render_template("edit_oportunidades.html", form=form, oportunidad=oportunidad[0])

@oportunidades_bp.route("/delete/<int:codigo_oportunidad>", methods=["GET", "POST"])
@login_required
def delete_oportunidad(codigo_oportunidad):
    oportunidad = oportunidad_client.get_by_key("codigo_oportunidad", codigo_oportunidad)
    if not oportunidad:
        flash("Oportunidad no encontrada", "error")
        return redirect(url_for("vistaOportunidad.list_oportunidades"))

    form = OportunidadForm()

    if request.method == "POST":
        response = oportunidad_client.delete_by_key("codigo_oportunidad", codigo_oportunidad)
        if response and response.get("estado") == 200:
            flash("Oportunidad eliminada correctamente", "success")
            return redirect(url_for("vistaOportunidad.list_oportunidades"))
        else:
            flash("Error al eliminar la oportunidad", "danger")

    return render_template("delete_oportunidades.html", form=form, oportunidad=oportunidad[0])


@oportunidades_bp.route("/detail/<int:codigo_oportunidad>", methods=["GET"])
@login_required
def detail_oportunidad(codigo_oportunidad):
    oportunidad = oportunidad_client.get_by_id("codigo_oportunidad", codigo_oportunidad)
    if not oportunidad:
        flash("Oportunidad no encontrada", "error")
        return redirect(url_for("vistaOportunidad.list_oportunidades"))
    return render_template("detail_oportunidades.html", oportunidad=oportunidad[0])


@oportunidades_bp.route("/confirmar/<int:codigo_oportunidad>", methods=["GET", "POST"])
@login_required
def confirmar_oportunidad(codigo_oportunidad):
    oportunidad = oportunidad_client.get_by_id("codigo_oportunidad", codigo_oportunidad)
    if not oportunidad:
        flash("Oportunidad no encontrada", "error")
        return redirect(url_for("vistaOportunidad.list_oportunidades"))

    form = OportunidadForm()

    if request.method == "POST" and request.form.get("confirmar"):
        mensaje_experto = request.form.get("mensaje_experto")
        oportunidad_client.confirm("codigo_oportunidad", codigo_oportunidad)
        flash("Oportunidad confirmada exitosamente", "success")
        return render_template("confirmar_oportunidades.html", form=form, oportunidad=oportunidad[0], mensaje_experto=mensaje_experto)

    return render_template("confirmar_oportunidades.html", form=form, oportunidad=oportunidad[0])
