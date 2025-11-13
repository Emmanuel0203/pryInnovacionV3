# app/views/vistaSolucion.py
from flask import (
    Blueprint, render_template, request, redirect, url_for, flash, session, current_app
)
from flask_login import current_user
from collections import Counter
from utils.api_client import APIClient
from utils.external_api import FocoInnovacionAPI, TipoInnovacionAPI
from forms.formsSoluciones import SolucionForm
from flask_login import login_required
import requests
from datetime import datetime


soluciones_bp = Blueprint(
    "vistaSolucion",
    __name__,
    template_folder="templates",
    url_prefix="/soluciones"
)

solucion_client = APIClient("solucion")

@soluciones_bp.route("/", methods=["GET"])
@login_required
def list_solucion():
    try:
        soluciones = solucion_client.get_all()
        focos_tipos = {
            "focos": solucion_client.fetch_endpoint_data("foco_innovacion"),
            "tipos": solucion_client.fetch_endpoint_data("tipo_innovacion")
        }

        # Mapear IDs a nombres para foco y tipo de innovación
        foco_map = {f['id_foco_innovacion']: f['name'] for f in focos_tipos['focos']}
        tipo_map = {t['id_tipo_innovacion']: t['name'] for t in focos_tipos['tipos']}

        # Agregar nombres a cada solución
        for solucion in soluciones:
            solucion['foco_innovacion_nombre'] = foco_map.get(solucion['id_foco_innovacion'], "Desconocido")
            solucion['tipo_innovacion_nombre'] = tipo_map.get(solucion['id_tipo_innovacion'], "Desconocido")

        current_app.logger.debug(f"Soluciones procesadas: {soluciones}")

        # Configurar las opciones dinámicas en el formulario
        form = SolucionForm()
        form.foco_innovacion.choices = [(f['id_foco_innovacion'], f['name']) for f in focos_tipos['focos']]
        form.tipo_innovacion.choices = [(t['id_tipo_innovacion'], t['name']) for t in focos_tipos['tipos']]

        # Verificar que las opciones se asignaron correctamente
        current_app.logger.debug(f"Opciones de foco_innovacion: {form.foco_innovacion.choices}")
        current_app.logger.debug(f"Opciones de tipo_innovacion: {form.tipo_innovacion.choices}")

    except Exception as e:
        current_app.logger.exception("Error al procesar soluciones")
        flash(f"Error al obtener las soluciones: {e}", "danger")
        soluciones = []
        form = SolucionForm()
        form.foco_innovacion.choices = []
        form.tipo_innovacion.choices = []

    current_app.logger.debug(f"Datos de soluciones: {soluciones}")

    return render_template("list_soluciones.html", soluciones=soluciones, form=form)




@soluciones_bp.route("/<int:codigo_solucion>", methods=["GET"])
@login_required
def get_solucion(codigo_solucion):
    # ✅ AGREGAR DEBUG
    current_app.logger.info(f"🔍 Solicitando solución con código: {codigo_solucion}")
    
    solution = solucion_client.get_by_id("codigo_solucion", codigo_solucion)
    
    # ✅ AGREGAR DEBUG
    current_app.logger.info(f"📦 Solución recibida: {solution}")
    
    if not solution:
        flash("Solución no encontrada", "error")
        return redirect(url_for("vistaSolucion.list_solucion"))
    
    # ✅ AGREGAR DEBUG
    current_app.logger.info(f"📊 Código de la solución obtenida: {solution[0].get('codigo_solucion')}")
    
    # Obtener nombres de tipo y foco
    try:
        focos_tipos = {
            "focos": solucion_client.fetch_endpoint_data("foco_innovacion"),
            "tipos": solucion_client.fetch_endpoint_data("tipo_innovacion")
        }
        
        foco_map = {f['id_foco_innovacion']: f['name'] for f in focos_tipos['focos']}
        tipo_map = {t['id_tipo_innovacion']: t['name'] for t in focos_tipos['tipos']}
        
        solution[0]['tipo_innovacion_nombre'] = tipo_map.get(solution[0]['id_tipo_innovacion'], 'Desconocido')
        solution[0]['foco_innovacion_nombre'] = foco_map.get(solution[0]['id_foco_innovacion'], 'Desconocido')
    except Exception as e:
        current_app.logger.error(f"Error al obtener nombres de tipo/foco: {e}")
    
    return render_template("detail_soluciones.html", solucion=solution[0])



@soluciones_bp.route("/create", methods=["GET", "POST"])
@login_required
def create_solucion():
    form = SolucionForm()

    # Cargar opciones dinámicamente desde la API
    try:
        focos_tipos = {
            "focos": solucion_client.fetch_endpoint_data("foco_innovacion"),
            "tipos": solucion_client.fetch_endpoint_data("tipo_innovacion")
        }
        form.foco_innovacion.choices = [(f['id_foco_innovacion'], f['name']) for f in focos_tipos['focos']]
        form.tipo_innovacion.choices = [(t['id_tipo_innovacion'], t['name']) for t in focos_tipos['tipos']]
        print(f"[DEBUG] Opciones cargadas: Focos: {focos_tipos['focos']}, Tipos: {focos_tipos['tipos']}")
    except Exception as e:
        print("[ERROR] Error al cargar opciones de innovación", e)
        form.foco_innovacion.choices = []
        form.tipo_innovacion.choices = []

    if form.validate_on_submit():
        print("[DEBUG] Formulario válido. Enviando datos a la API...")
        archivo = request.files.get('archivo_multimedia')
        archivo_multimedia = archivo.filename if archivo else None

        payload = {
            "id_tipo_innovacion": form.tipo_innovacion.data,
            "id_foco_innovacion": form.foco_innovacion.data,
            "titulo": form.titulo.data,
            "descripcion": form.descripcion.data,
            "palabras_claves": form.palabras_claves.data,
            "recursos_requeridos": form.recursos_requeridos.data,
            "archivo_multimedia": archivo_multimedia,
            "creador_por": session.get("user_email"),
            "desarrollador_por": "1",  # Valor por defecto
            "area_unidad_desarrollo": "1",  # Valor por defecto
            "estado": True  # Valor por defecto
        }

        # Validar que los campos obligatorios estén presentes y cumplan con los requisitos
        if not payload.get("id_tipo_innovacion") or not payload.get("id_foco_innovacion"):
            print("[ERROR] Los campos 'id_tipo_innovacion' y 'id_foco_innovacion' son obligatorios.")
            flash("Error: Los campos 'Tipo de Innovación' y 'Foco de Innovación' son obligatorios.", "danger")
            return render_template("create_soluciones.html", form=form)

        if not payload.get("titulo") or len(payload["titulo"]) > 255:
            print("[ERROR] El campo 'titulo' es obligatorio y no debe exceder 255 caracteres.")
            flash("Error: El título es obligatorio y no debe exceder 255 caracteres.", "danger")
            return render_template("create_soluciones.html", form=form)

        if not payload.get("descripcion"):
            print("[ERROR] El campo 'descripcion' es obligatorio.")
            flash("Error: La descripción es obligatoria.", "danger")
            return render_template("create_soluciones.html", form=form)

        # Asegurarse de enviar el payload como un objeto JSON
        # Eliminar la línea que convierte el payload en un arreglo
        current_app.logger.debug(f"[DEBUG] Payload preparado para enviar: {payload}")
        current_app.logger.debug(f"[DEBUG] Enviando solicitud POST a {solucion_client.base_url}/solucion")
        current_app.logger.debug(f"[DEBUG] Headers utilizados: {{'Content-Type': 'application/json'}}")

        response = solucion_client.insert_data(payload)  # Enviar el objeto JSON directamente

        # Log detallado de la respuesta de la API
        # Registrar más detalles de la respuesta de la API
        if response:
            current_app.logger.debug(f"[DEBUG] Respuesta completa de la API: {response}")
            if 'content' in response:
                current_app.logger.debug(f"[DEBUG] Contenido de la respuesta: {response['content']}")
        else:
            current_app.logger.error("[ERROR] No se recibió respuesta de la API")

        # Mejorar el manejo de errores para registrar el mensaje de error de la API
        # Implementar Post/Redirect/Get para evitar reenvío del formulario
        if response and response.get("status_code") == 201:
            current_app.logger.info("Redirigiendo a la lista de soluciones después de creación exitosa.")
            flash("Solución creada exitosamente.", "success")
            return redirect(url_for("vistaSolucion.list_solucion"))

        # En caso de error, mostrar mensaje y mantener el formulario
        error_message = response.get("mensaje", "Error desconocido") if response else "Sin respuesta del API"
        current_app.logger.error(f"Error al crear la solución: {error_message}")
        flash(f"Error al crear la solución: {error_message}", "danger")

    # Si no se valida el formulario, renderizar nuevamente con errores
    return render_template("create_soluciones.html", form=form)


# ================================================
# 🧩 EDITAR SOLUCIÓN (UPDATE)
# ================================================
@soluciones_bp.route("/update/<int:codigo_solucion>", methods=["GET", "POST"])
@login_required
def update_solucion(codigo_solucion):
    # ============================
    # 1️⃣ Obtener solución actual
    # ============================
    solution_response = solucion_client.get_by_key("codigo_solucion", codigo_solucion)
    current_app.logger.debug(f"[DEBUG] Respuesta bruta de API: {solution_response}")

    # Manejar distintas formas de respuesta
    if isinstance(solution_response, dict):
        solution = solution_response.get("data", [])
    elif isinstance(solution_response, list):
        solution = solution_response
    else:
        solution = []

    if not solution:
        flash("Solución no encontrada", "error")
        return redirect(url_for("vistaSolucion.list_solucion"))

    solution = solution[0]  # tomamos el primer registro

    # ============================
    # 2️⃣ Cargar opciones dinámicas
    # ============================
    try:
        focos_tipos = {
            "focos": solucion_client.fetch_endpoint_data("foco_innovacion"),
            "tipos": solucion_client.fetch_endpoint_data("tipo_innovacion")
        }
    except Exception as e:
        current_app.logger.exception("Error al cargar opciones dinámicas")
        focos_tipos = {"focos": [], "tipos": []}

    # ============================
    # 3️⃣ Inicializar formulario
    # ============================
    form = SolucionForm(data=solution)
    form.foco_innovacion.choices = [
        (f['id_foco_innovacion'], f['name']) for f in focos_tipos['focos']
    ]
    form.tipo_innovacion.choices = [
        (t['id_tipo_innovacion'], t['name']) for t in focos_tipos['tipos']
    ]

    # ============================
    # 4️⃣ Procesar formulario
    # ============================
    if request.method == "POST" and form.validate_on_submit():
        current_app.logger.debug(f"[DEBUG] Estado del form: {form.estado.data}")

        payload = {
            "id_tipo_innovacion": form.tipo_innovacion.data,
            "id_foco_innovacion": form.foco_innovacion.data,
            "titulo": form.titulo.data,
            "descripcion": form.descripcion.data,
            "palabras_claves": form.palabras_claves.data,
            "recursos_requeridos": form.recursos_requeridos.data,
            "archivo_multimedia": solution.get("archivo_multimedia"),
            "creador_por": solution.get("creador_por"),
            "desarrollador_por": solution.get("desarrollador_por"),
            "area_unidad_desarrollo": solution.get("area_unidad_desarrollo"),
            "estado": True if form.estado.data else False
        }

        current_app.logger.debug(f"[DEBUG] Payload enviado a API: {payload}")

        response = solucion_client.update_by_key("codigo_solucion", codigo_solucion, payload)

        # ============================
        # 5️⃣ Validar respuesta y redirigir
        # ============================
        if response and response.get("status_code") in [200, 201]:
            flash("✅ Solución actualizada correctamente", "success")
            return redirect(url_for("vistaSolucion.list_solucion"))
        else:
            current_app.logger.error(f"❌ Error al actualizar solución: {response}")
            flash("❌ Error al actualizar la solución", "error")
            return redirect(url_for("vistaSolucion.list_solucion"))  # 🔁 redirige igual aunque falle

    # ============================
    # 6️⃣ Renderizar plantilla (solo si GET)
    # ============================
    return render_template("update_soluciones.html", form=form, solution=solution)


@soluciones_bp.route("/delete/<int:codigo_solucion>", methods=["GET", "POST"])
@login_required
def delete_solucion(codigo_solucion):
    solution = solucion_client.get_by_key("codigo_solucion", codigo_solucion)
    if not solution:
        flash("Solución no encontrada", "error")
        return redirect(url_for("vistaSolucion.list_solucion"))

    form = SolucionForm()

    if request.method == "POST":
        response = solucion_client.delete_by_key("codigo_solucion", codigo_solucion)

        if response and response.get("estado") == 200:
            flash("Solución eliminada correctamente", "success")
            return redirect(url_for("vistaSolucion.list_solucion"))
        else:
            flash("Error al eliminar la solución", "error")

    return render_template("delete_soluciones.html", form=form, solucion=solution[0])


@soluciones_bp.route("/detail/<int:codigo_solucion>", methods=["GET"])
@login_required
def detail_solucion(codigo_solucion):
    """Vista para ver detalles de una solución con tipo y foco de innovación"""
    
    # ✅ CAMBIO: usar get_by_key en lugar de get_by_id
    solution = solucion_client.get_by_key("codigo_solucion", codigo_solucion)
    
    # ✅ AGREGAR DEBUG
    current_app.logger.info(f"🔍 Buscando solución con código: {codigo_solucion}")
    current_app.logger.info(f"📦 Solución encontrada: {solution}")
    
    if not solution or len(solution) == 0:
        flash("Solución no encontrada", "error")
        return redirect(url_for("vistaSolucion.list_solucion"))
    
    # ✅ Obtener nombres de tipo y foco
    try:
        focos_tipos = {
            "focos": solucion_client.fetch_endpoint_data("foco_innovacion"),
            "tipos": solucion_client.fetch_endpoint_data("tipo_innovacion")
        }
        
        foco_map = {f['id_foco_innovacion']: f['name'] for f in focos_tipos['focos']}
        tipo_map = {t['id_tipo_innovacion']: t['name'] for t in focos_tipos['tipos']}
        
        solution[0]['tipo_innovacion_nombre'] = tipo_map.get(solution[0]['id_tipo_innovacion'], 'Desconocido')
        solution[0]['foco_innovacion_nombre'] = foco_map.get(solution[0]['id_foco_innovacion'], 'Desconocido')
        
        current_app.logger.info(f"✅ Código de solución procesado: {solution[0].get('codigo_solucion')}")
    except Exception as e:
        current_app.logger.error(f"❌ Error al obtener nombres de tipo/foco: {e}")
    
    return render_template("detail_soluciones.html", solucion=solution[0])


@soluciones_bp.route("/confirmar/<int:codigo_solucion>", methods=["GET", "POST"])
@login_required
def confirmar_solucion(codigo_solucion):
    solution = solucion_client.get_by_id("codigo_solucion", codigo_solucion)
    if not solution:
        flash("Solución no encontrada", "error")
        return redirect(url_for("vistaSolucion.list_solucion"))

    form = SolucionForm()

    if request.method == "POST" and request.form.get("confirmar"):
        mensaje_experto = request.form.get("mensaje_experto")
        solucion_client.confirm("codigo_solucion", codigo_solucion)
        flash("Solución confirmada exitosamente", "success")
        return render_template("confirmar_soluciones.html", form=form, solucion=solution[0], mensaje_experto=mensaje_experto)

    return render_template("confirmar_soluciones.html", form=form, solucion=solution[0])


@soluciones_bp.route("/calendario", methods=["GET"])
@login_required
def vistacalendario():
    return render_template("calendar.html")

from collections import Counter

@soluciones_bp.route('/top-generadores')
@login_required
def top_generadores():
    """Top 10 generadores de soluciones"""
    try:
        soluciones = solucion_client.get_all() or []
        creador_key = lambda solucion: (
            solucion.get("creador_por") or 
            solucion.get("usuario") or 
            solucion.get("autor") or 
            "Anónimo"
        )
        top_generadores = Counter(
            creador_key(s) for s in soluciones
        ).most_common(10)
    except Exception as e:
        current_app.logger.exception("Error al obtener top generadores de soluciones")
        flash(f"Error al cargar el top de generadores: {e}", "danger")
        top_generadores = []
    
    # ✅ CAMBIA ESTA LÍNEA:
    return render_template(
        "top_generadoresSolu.html",  # ← Nombre correcto del archivo
        top_generadores=top_generadores
    )


@soluciones_bp.route("/mercado", methods=["GET"])
@login_required
def mercado():
    """Mercado de soluciones - solo muestra soluciones aprobadas"""
    try:
        soluciones_mercado = solucion_client.get_all() or []
        soluciones_mercado = [s for s in soluciones_mercado if s.get('estado') == True]
        
        focos_tipos = {
            "focos": solucion_client.fetch_endpoint_data("foco_innovacion"),
            "tipos": solucion_client.fetch_endpoint_data("tipo_innovacion")
        }
        
        foco_map = {f['id_foco_innovacion']: f['name'] for f in focos_tipos['focos']}
        tipo_map = {t['id_tipo_innovacion']: t['name'] for t in focos_tipos['tipos']}
        
        for solucion in soluciones_mercado:
            solucion['foco_innovacion_nombre'] = foco_map.get(solucion['id_foco_innovacion'], 'Desconocido')
            solucion['tipo_innovacion_nombre'] = tipo_map.get(solucion['id_tipo_innovacion'], 'Desconocido')
            
            fecha = solucion.get("fecha_creacion")
            if isinstance(fecha, str):
                try:
                    solucion["fecha_creacion"] = datetime.strptime(fecha[:10], "%Y-%m-%d")
                except Exception:
                    solucion["fecha_creacion"] = None
            elif fecha is None:
                solucion["fecha_creacion"] = None
                
    except Exception as e:
        current_app.logger.exception("Error al obtener soluciones para el mercado")
        flash(f"Error al obtener soluciones del mercado: {e}", "danger")
        soluciones_mercado = []
    
    # ✅ CAMBIA ESTA LÍNEA:
    return render_template(
        "mercado_soluciones.html",  # ← Nombre correcto del archivo
        soluciones_mercado=soluciones_mercado
    )