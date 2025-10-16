# app/views/vistaSolucion.py
from flask import (
    Blueprint, render_template, request, redirect, url_for, flash, session, current_app
)
from flask_login import current_user
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
    solution = solucion_client.get_by_id("codigo_solucion", codigo_solucion)
    if not solution:
        flash("Solución no encontrada", "error")
        return redirect(url_for("vistaSolucion.list_solucion"))
    return render_template("detail_soluciones.html", solution=solution[0])



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



@soluciones_bp.route("/update/<int:codigo_solucion>", methods=["GET", "POST"])
@login_required
def update_solucion(codigo_solucion):
    solution = solucion_client.get_by_key("codigo_solucion", codigo_solucion)
    if not solution:
        flash("Solución no encontrada", "error")
        return redirect(url_for("vistaSolucion.list_solucion"))

    # Cargar opciones dinámicas desde la API
    try:
        focos_tipos = {
            "focos": solucion_client.fetch_endpoint_data("foco_innovacion"),
            "tipos": solucion_client.fetch_endpoint_data("tipo_innovacion")
        }
    except Exception as e:
        current_app.logger.exception("Error al cargar opciones dinámicas")
        focos_tipos = {
            "focos": [],
            "tipos": []
        }

    form = SolucionForm(data=solution[0])
    form.foco_innovacion.choices = [(f['id_foco_innovacion'], f['name']) for f in focos_tipos['focos']]
    form.tipo_innovacion.choices = [(t['id_tipo_innovacion'], t['name']) for t in focos_tipos['tipos']]

    if request.method == "POST" and form.validate_on_submit():
        payload = {
            "id_tipo_innovacion": form.tipo_innovacion.data,
            "id_foco_innovacion": form.foco_innovacion.data,
            "titulo": form.titulo.data,
            "descripcion": form.descripcion.data,
            "palabras_claves": form.palabras_claves.data,
            "recursos_requeridos": form.recursos_requeridos.data,
            "archivo_multimedia": None,
            "creador_por": solution[0].get("creador_por"),
            "desarrollador_por": solution[0].get("desarrollador_por"),
            "area_unidad_desarrollo": solution[0].get("area_unidad_desarrollo"),
            "estado": solution[0].get("estado")
        }

        response = solucion_client.update_by_key("codigo_solucion", codigo_solucion, payload)

        if response and response.get("estado") == 200:
            flash("Solución actualizada correctamente", "success")
            return redirect(url_for("vistaSolucion.list_solucion"))
        else:
            flash("Error al actualizar la solución", "error")

    return render_template("update_soluciones.html", form=form, solution=solution[0])



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
    solution = solucion_client.get_by_id("codigo_solucion", codigo_solucion)
    if not solution:
        flash("Solución no encontrada", "error")
        return redirect(url_for("vistaSolucion.list_solucion"))
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
