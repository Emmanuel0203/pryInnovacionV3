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
        focos = solucion_client.fetch_endpoint_data("foco_innovacion")
        tipos = solucion_client.fetch_endpoint_data("tipo_innovacion")

        # Log the fetched data for debugging
        current_app.logger.info(f"Focos: {focos}, Tipos: {tipos}")

        # Integrate with SolucionForm
        form = SolucionForm()
        form.load_dynamic_choices(focos, tipos)
    except Exception as e:
        current_app.logger.exception("Error al obtener soluciones")
        flash(f"Error al obtener las soluciones: {e}", "danger")
        soluciones = []
        focos = []
        tipos = []
        form = SolucionForm()

    return render_template("list_soluciones.html", soluciones=soluciones, focos=focos, tipos=tipos, form=form)




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
        focos = solucion_client.fetch_endpoint_data("foco_innovacion")
        tipos = solucion_client.fetch_endpoint_data("tipo_innovacion")
        form.foco_innovacion.choices = [(f['id_foco_innovacion'], f['name']) for f in focos]
        form.tipo_innovacion.choices = [(t['id_tipo_innovacion'], t['name']) for t in tipos]
    except Exception as e:
        flash("Error al cargar opciones de innovación", "danger")
        form.foco_innovacion.choices = []
        form.tipo_innovacion.choices = []

    if form.validate_on_submit():
        payload = {
            "titulo": form.titulo.data,
            "descripcion": form.descripcion.data,
            "palabras_claves": form.palabras_claves.data,
            "recursos_requeridos": form.recursos_requeridos.data,
            "fecha_creacion": form.fecha_creacion.data.strftime('%Y-%m-%d') if form.fecha_creacion.data else None,
            "tipo_innovacion": form.tipo_innovacion.data,
            "foco_innovacion": form.foco_innovacion.data,
            "usuario_email": session.get("user_email"),
            # Puedes agregar aquí el manejo de archivo si lo necesitas
        }
        response = solucion_client.create(payload)
        if response and response.status_code == 201:
            flash("Solución creada exitosamente", "success")
            return redirect(url_for("vistaSolucion.list_solucion"))
        else:
            flash("Error al crear la solución", "danger")

    return render_template("create_soluciones.html", form=form)



@soluciones_bp.route("/update/<int:codigo_solucion>", methods=["GET", "POST"])
@login_required
def update_solucion(codigo_solucion):
    solution = solucion_client.get_by_id("codigo_solucion", codigo_solucion)
    if not solution:
        flash("Solución no encontrada", "error")
        return redirect(url_for("vistaSolucion.list_solucion"))

    # Convertir fecha_creacion a datetime si es una cadena
    if isinstance(solution[0].get("fecha_creacion"), str):
        try:
            solution[0]["fecha_creacion"] = datetime.strptime(solution[0]["fecha_creacion"], "%Y-%m-%d")
        except ValueError:
            flash("Formato de fecha inválido en la solución", "danger")
            return redirect(url_for("vistaSolucion.list_solucion"))

    form = SolucionForm(data=solution[0])

    if request.method == "POST" and form.validate_on_submit():
        payload = {
            "titulo": form.titulo.data,
            "descripcion": form.descripcion.data,
            "fecha_creacion": form.fecha_creacion.data.strftime('%Y-%m-%d') if form.fecha_creacion.data else None,
        }
        solucion_client.update("codigo_solucion", codigo_solucion, payload)
        flash("Solución actualizada correctamente", "success")
        return redirect(url_for("vistaSolucion.list_solucion"))

    return render_template("update_soluciones.html", form=form, solution=solution[0])



@soluciones_bp.route("/delete/<int:codigo_solucion>", methods=["GET", "POST"])
@login_required
def delete_solucion(codigo_solucion):
    solution = solucion_client.get_by_id("codigo_solucion", codigo_solucion)
    if not solution:
        flash("Solución no encontrada", "error")
        return redirect(url_for("vistaSolucion.list_solucion"))

    form = SolucionForm()

    if request.method == "POST":
        solucion_client.delete("codigo_solucion", codigo_solucion)
        flash("Solución eliminada correctamente", "success")
        return redirect(url_for("vistaSolucion.list_solucion"))

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
