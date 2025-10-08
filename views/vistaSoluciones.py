# app/views/vistaSolucion.py
from flask import (
    Blueprint, render_template, request, redirect, url_for, flash, session, current_app
)
from flask_login import current_user
from utils.api_client import APIClient
from utils.external_api import FocoInnovacionAPI, TipoInnovacionAPI
from forms.formsSoluciones import SolucionForm
from flask_login import login_required


soluciones_bp = Blueprint(
    "vistaSolucion",
    __name__,
    template_folder="templates",
    url_prefix="/soluciones"
)

solucion_client = APIClient("solucion")

@soluciones_bp.route("/", methods=["GET"])
@login_required
def list_soluciones():
    try:
        soluciones = solucion_client.get_all()
    except Exception as e:
        current_app.logger.exception("Error al obtener soluciones")
        flash(f"Error al obtener las soluciones: {e}", "danger")
        soluciones = []

    return render_template("list_soluciones.html", soluciones=soluciones)




@soluciones_bp.route("/<int:solucion_id>", methods=["GET"])
@login_required
def get_solution(solucion_id):
    solution = solucion_client.get_by_id("id", solucion_id)
    if not solution:
        flash("Solución no encontrada", "error")
        return redirect(url_for("vistaSolucion.list_soluciones"))
    return render_template("detail_soluciones.html", solution=solution[0])



@soluciones_bp.route("/create", methods=["GET", "POST"])
@login_required
def create_solucion():
    import requests
    form = SolucionForm()

    # Cargar opciones dinámicamente desde la API
    try:
        focos = requests.get("http://localhost:5186/api/foco_innovacion").json().get("datos", [])
        tipos = requests.get("http://localhost:5186/api/tipo_innovacion").json().get("datos", [])
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
            return redirect(url_for("vistaSolucion.list_soluciones"))
        else:
            flash("Error al crear la solución", "danger")

    return render_template("create_soluciones.html", form=form)



@soluciones_bp.route("/update/<int:solucion_id>", methods=["GET", "POST"])
@login_required
def update_solution(solucion_id):
    solution = solucion_client.get_by_id("id", solucion_id)
    if not solution:
        flash("Solución no encontrada", "error")
        return redirect(url_for("vistaSolucion.list_soluciones"))

    if request.method == "POST":
        payload = {
            "titulo": request.form.get("titulo"),
            "descripcion": request.form.get("descripcion"),
        }
        solucion_client.update("id", solucion_id, payload)
        flash("Solución actualizada correctamente", "success")
        return redirect(url_for("vistaSolucion.list_soluciones"))

    return render_template("update_soluciones.html", solution=solution[0])



@soluciones_bp.route("/delete/<int:solucion_id>", methods=["POST"])
@login_required
def delete_solution(solucion_id):
    solucion_client.delete("id", solucion_id)
    flash("Solución eliminada correctamente", "success")
    return redirect(url_for("vistaSolucion.list_soluciones"))
