from flask import (
    Blueprint, render_template, request, redirect, url_for, flash, session, current_app
)
from flask_login import login_required
from utils.api_client import APIClient
from forms.formsOportunidades import OportunidadForm
from datetime import datetime
from collections import Counter
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
    """Vista para listar oportunidades con filtros por tipo, foco y estado."""

    # Inicializar clientes para las APIs
    tipo_client = APIClient('tipo_innovacion')
    foco_client = APIClient('foco_innovacion')

    # --- Obtener filtros desde la URL ---
    tipo_innovacion = request.args.get('tipo_innovacion')
    foco_innovacion = request.args.get('foco_innovacion')
    estado = request.args.get('estado')

    try:
        # --- Obtener datos desde la API ---
        oportunidades = oportunidad_client.get_all() or []
        tipos = tipo_client.get_all() or []
        focos = foco_client.get_all() or []
    except Exception as e:
        flash(f"Ocurrió un error al obtener los datos: {e}", "danger")
        oportunidades, tipos, focos = [], [], []

    # --- Crear diccionarios para mapear nombres ---
    tipo_dict = {t.get('id_tipo_innovacion'): t.get('name', '') for t in tipos}
    foco_dict = {f.get('id_foco_innovacion'): f.get('name', '') for f in focos}

    # --- Aplicar filtros ---
    if tipo_innovacion:
        oportunidades = [o for o in oportunidades if str(o.get('id_tipo_innovacion')) == tipo_innovacion]

    if foco_innovacion:
        oportunidades = [o for o in oportunidades if str(o.get('id_foco_innovacion')) == foco_innovacion]

    if estado in ['0', '1']:
        estado_bool = estado == '1'
        oportunidades = [o for o in oportunidades if o.get('estado') == estado_bool]

    # --- Renderizar plantilla ---
    return render_template(
        'list_oportunidades.html',
        oportunidades=oportunidades,
        tipos=tipos,
        focos=focos,
        tipo_dict=tipo_dict,
        foco_dict=foco_dict,
        filtros={
            'tipo_innovacion': tipo_innovacion,
            'foco_innovacion': foco_innovacion,
            'estado': estado
        }
    )

@oportunidades_bp.route("/create", methods=["GET", "POST"])
@login_required
def create_oportunidad():
    """
    Crea una nueva oportunidad.
    Carga dinámicamente los focos y tipos de innovación desde la API
    y permite subir archivos multimedia de forma segura.
    """
    form = OportunidadForm()

    # ======================================================
    # 🔹 1. Cargar focos y tipos desde el cliente API
    # ======================================================
    try:
        focos = oportunidad_client.fetch_endpoint_data("foco_innovacion")
        tipos = oportunidad_client.fetch_endpoint_data("tipo_innovacion")

        form.load_dynamic_choices(focos, tipos)
        print(f"[DEBUG] Focos cargados: {focos}")
        print(f"[DEBUG] Tipos cargados: {tipos}")

    except Exception as e:
        current_app.logger.error(f"[ERROR] No se pudieron cargar los focos/tipos: {e}")
        form.id_foco_innovacion.choices = []
        form.id_tipo_innovacion.choices = []
        flash("Error al cargar los tipos o focos de innovación.", "danger")

    # ======================================================
    # 🔹 2. Validar y procesar el formulario
    # ======================================================
    if form.validate_on_submit():
        print("[DEBUG] Formulario válido. Procesando...")

        # --------------------------------------------
        # 📁 Manejo de archivo multimedia
        # --------------------------------------------
        archivo_url = ""
        archivo = form.archivo_multimedia.data

        if archivo and archivo.filename:
            try:
                upload_folder = os.path.join(current_app.root_path, "static", "uploads")
                os.makedirs(upload_folder, exist_ok=True)

                filename = secure_filename(archivo.filename)
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_")
                unique_filename = f"{timestamp}{filename}"
                file_path = os.path.join(upload_folder, unique_filename)

                archivo.save(file_path)
                archivo_url = f"uploads/{unique_filename}"

                print(f"[DEBUG] Archivo guardado correctamente en {file_path}")
            except Exception as e:
                current_app.logger.error(f"[ERROR] Falló el guardado del archivo: {e}")
                flash("Error al guardar el archivo multimedia.", "danger")
                return render_template("create_oportunidades.html", form=form)

        # --------------------------------------------
        # 🧩 Construcción del payload
        # --------------------------------------------
        payload = {
            "id_tipo_innovacion": form.id_tipo_innovacion.data,
            "id_foco_innovacion": form.id_foco_innovacion.data,
            "titulo": form.titulo.data.strip(),
            "descripcion": form.descripcion.data.strip(),
            "palabras_claves": form.palabras_claves.data.strip(),
            "recursos_requeridos": form.recursos_requeridos.data,
            "archivo_multimedia": archivo_url,
            "fecha_creacion": datetime.now().strftime("%Y-%m-%d"),
            "creador_por": session.get("user_email", ""),
            "estado": form.estado.data or False
        }

        current_app.logger.debug(f"[DEBUG] Payload final: {payload}")

        # ======================================================
        # 🔹 3. Enviar a la API
        # ======================================================
        try:
            response = oportunidad_client.insert_data(payload)
            current_app.logger.debug(f"[DEBUG] Respuesta API: {response}")

            if response and response.get("status_code") == 201:
                flash("Oportunidad creada exitosamente.", "success")
                return redirect(url_for("vistaOportunidad.list_oportunidades"))
            else:
                error_msg = response.get("mensaje", "Error desconocido") if response else "Sin respuesta del API"
                flash(f"Error al crear la oportunidad: {error_msg}", "danger")

        except Exception as e:
            current_app.logger.error(f"[ERROR] Falló la comunicación con la API: {e}")
            flash("Error al conectar con el servicio de oportunidades.", "danger")

    else:
        # Si el formulario no es válido, mostrar errores
        if request.method == "POST":
            current_app.logger.warning(f"[WARN] Formulario inválido: {form.errors}")
            flash("Por favor corrige los errores del formulario.", "warning")

    # ======================================================
    # 🔹 4. Renderizar plantilla
    # ======================================================
    return render_template("create_oportunidades.html", form=form)


@oportunidades_bp.route("/update/<int:codigo_oportunidad>", methods=["GET", "POST"])
@login_required
def update_oportunidad(codigo_oportunidad):
    # 1️⃣ Obtener la oportunidad
    data = oportunidad_client.get_by_key("codigo_oportunidad", codigo_oportunidad)
    if not data or len(data) == 0:
        flash("Oportunidad no encontrada", "error")
        return redirect(url_for("vistaOportunidad.list_oportunidades"))

    oportunidad_data = data[0].copy()

    # 2️⃣ Normalizar IDs
    def to_int_safe(val):
        try:
            return int(val) if val is not None else None
        except Exception:
            return None

    selected_foco = to_int_safe(oportunidad_data.get("id_foco_innovacion"))
    selected_tipo = to_int_safe(oportunidad_data.get("id_tipo_innovacion"))

    # 3️⃣ Cargar focos y tipos
    try:
        focos = oportunidad_client.fetch_endpoint_data("foco_innovacion") or []
        tipos = oportunidad_client.fetch_endpoint_data("tipo_innovacion") or []
    except Exception as e:
        current_app.logger.exception("Error al cargar focos/tipos desde la API")
        focos, tipos = [], []

    # 4️⃣ Crear formulario y cargar choices
    form = OportunidadForm()
    form.load_dynamic_choices(focos, tipos, selected_foco, selected_tipo)

    # 5️⃣ Precargar datos (GET)
    if request.method == "GET":
        form.process(data=oportunidad_data)

    # 6️⃣ POST → procesar actualización
    if request.method == "POST" and form.validate_on_submit():
        payload = {
            "id_tipo_innovacion": int(form.id_tipo_innovacion.data) if form.id_tipo_innovacion.data else None,
            "id_foco_innovacion": int(form.id_foco_innovacion.data) if form.id_foco_innovacion.data else None,
            "titulo": form.titulo.data,
            "descripcion": form.descripcion.data,
            "palabras_claves": form.palabras_claves.data,
            "recursos_requeridos": form.recursos_requeridos.data,
            "archivo_multimedia": oportunidad_data.get("archivo_multimedia"),
            "creador_por": oportunidad_data.get("creador_por"),
            "estado": bool(form.estado.data)
        }

        current_app.logger.debug(f"[update_oportunidad] payload: {payload}")

        response = oportunidad_client.update_by_key("codigo_oportunidad", codigo_oportunidad, payload)

        ok = False
        if isinstance(response, dict):
            ok = response.get("estado") in (200, "200") or response.get("status_code") in (200, "200")
        elif hasattr(response, "status_code"):
            ok = response.status_code in (200, 201)

        if ok:
            flash("Oportunidad actualizada correctamente", "success")
            return redirect(url_for("vistaOportunidad.list_oportunidades"))
        else:
            flash("Error al actualizar la oportunidad", "error")

    # 7️⃣ Renderizar plantilla
    return render_template("edit_oportunidades.html", form=form, oportunidad=oportunidad_data)

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
    """Vista para ver detalles de una oportunidad con tipo y foco de innovación"""
    
    oportunidad = oportunidad_client.get_by_key("codigo_oportunidad", codigo_oportunidad)
    
    if not oportunidad or not isinstance(oportunidad, list) or len(oportunidad) == 0:
        flash("Oportunidad no encontrada", "error")
        return redirect(url_for("vistaOportunidad.list_oportunidades"))
    
    oportunidad_data = oportunidad[0]
    
    try:
        tipos = oportunidad_client.fetch_endpoint_data("tipo_innovacion") or []
        focos = oportunidad_client.fetch_endpoint_data("foco_innovacion") or []
        
        tipo_dict = {t.get('id_tipo_innovacion'): t.get('name', 'No especificado') for t in tipos}
        foco_dict = {f.get('id_foco_innovacion'): f.get('name', 'No especificado') for f in focos}
        
        id_tipo = oportunidad_data.get('id_tipo_innovacion')
        id_foco = oportunidad_data.get('id_foco_innovacion')
        
        oportunidad_data['tipo_innovacion_nombre'] = tipo_dict.get(id_tipo, 'No especificado')
        oportunidad_data['foco_innovacion_nombre'] = foco_dict.get(id_foco, 'No especificado')
        
        current_app.logger.debug(f"Oportunidad {codigo_oportunidad} - Tipo: {oportunidad_data['tipo_innovacion_nombre']}, Foco: {oportunidad_data['foco_innovacion_nombre']}")
        
    except Exception as e:
        current_app.logger.exception(f"Error al cargar tipo/foco: {e}")
        oportunidad_data['tipo_innovacion_nombre'] = 'No especificado'
        oportunidad_data['foco_innovacion_nombre'] = 'No especificado'
    
    return render_template("detail_oportunidades.html", oportunidad=oportunidad_data)


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

@oportunidades_bp.route("/mercado", methods=["GET"])
@login_required
def mercado():
    """Mercado de oportunidades - solo muestra oportunidades activas"""
    try:
        oportunidades_mercado = oportunidad_client.get_all() or []
        oportunidades_mercado = [o for o in oportunidades_mercado if o.get('estado') == True]
        
        focos_tipos = {
            "focos": oportunidad_client.fetch_endpoint_data("foco_innovacion"),
            "tipos": oportunidad_client.fetch_endpoint_data("tipo_innovacion")
        }
        
        foco_map = {f['id_foco_innovacion']: f['name'] for f in focos_tipos['focos']}
        tipo_map = {t['id_tipo_innovacion']: t['name'] for t in focos_tipos['tipos']}
        
        for oportunidad in oportunidades_mercado:
            oportunidad['foco_innovacion_nombre'] = foco_map.get(oportunidad['id_foco_innovacion'], 'Desconocido')
            oportunidad['tipo_innovacion_nombre'] = tipo_map.get(oportunidad['id_tipo_innovacion'], 'Desconocido')
            
            fecha = oportunidad.get("fecha_creacion")
            if isinstance(fecha, str):
                try:
                    oportunidad["fecha_creacion"] = datetime.strptime(fecha[:10], "%Y-%m-%d")
                except Exception:
                    oportunidad["fecha_creacion"] = None
            elif fecha is None:
                oportunidad["fecha_creacion"] = None
                
    except Exception as e:
        current_app.logger.exception("Error al obtener oportunidades para el mercado")
        flash(f"Error al obtener oportunidades del mercado: {e}", "danger")
        oportunidades_mercado = []
    
    return render_template(
        "mercado_oportunidades.html",
        oportunidades_mercado=oportunidades_mercado
    )

@oportunidades_bp.route('/top-generadores')
@login_required
def top_generadores():
    """Top 10 generadores de oportunidades"""
    try:
        oportunidades = oportunidad_client.get_all() or []
        creador_key = lambda oportunidad: (
            oportunidad.get("creador_por") or 
            oportunidad.get("usuario") or 
            oportunidad.get("autor") or 
            "Anónimo"
        )
        top_generadores = Counter(
            creador_key(o) for o in oportunidades
        ).most_common(10)
    except Exception as e:
        current_app.logger.exception("Error al obtener top generadores de oportunidades")
        flash(f"Error al cargar el top de generadores: {e}", "danger")
        top_generadores = []
    
    return render_template(
        "top_generadores.html",
        top_generadores=top_generadores
    )