from flask import (
    Blueprint, render_template, request, redirect, url_for, flash, session, current_app
)
from flask_login import login_required
from utils.api_client import APIClient
from forms.formsOportunidades import OportunidadForm
from datetime import datetime


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
        oportunidades = oportunidad_client.get_all()
        focos_tipos = {
            "focos": oportunidad_client.fetch_endpoint_data("foco_innovacion"),
            "tipos": oportunidad_client.fetch_endpoint_data("tipo_innovacion")
        }

        foco_map = {f['id_foco_innovacion']: f['name'] for f in focos_tipos['focos']}
        tipo_map = {t['id_tipo_innovacion']: t['name'] for t in focos_tipos['tipos']}

        for oportunidad in oportunidades:
            oportunidad['foco_innovacion_nombre'] = foco_map.get(oportunidad['id_foco_innovacion'], "Desconocido")
            oportunidad['tipo_innovacion_nombre'] = tipo_map.get(oportunidad['id_tipo_innovacion'], "Desconocido")

        form = OportunidadForm()
        form.foco_innovacion.choices = [(f['id_foco_innovacion'], f['name']) for f in focos_tipos['focos']]
        form.tipo_innovacion.choices = [(t['id_tipo_innovacion'], t['name']) for t in focos_tipos['tipos']]

    except Exception as e:
        current_app.logger.exception("Error al procesar oportunidades")
        flash(f"Error al obtener las oportunidades: {e}", "danger")
        oportunidades = []
        form = OportunidadForm()
        form.foco_innovacion.choices = []
        form.tipo_innovacion.choices = []

    return render_template("list_oportunidades.html", oportunidades=oportunidades, form=form)

@oportunidades_bp.route("/create", methods=["GET", "POST"])
@login_required
def create_oportunidad():
    form = OportunidadForm()

    try:
        focos_tipos = {
            "focos": oportunidad_client.fetch_endpoint_data("foco_innovacion"),
            "tipos": oportunidad_client.fetch_endpoint_data("tipo_innovacion")
        }
        form.foco_innovacion.choices = [(f['id_foco_innovacion'], f['name']) for f in focos_tipos['focos']]
        form.tipo_innovacion.choices = [(t['id_tipo_innovacion'], t['name']) for t in focos_tipos['tipos']]
    except Exception as e:
        current_app.logger.exception("Error al cargar opciones dinámicas")
        form.foco_innovacion.choices = []
        form.tipo_innovacion.choices = []

    if form.validate_on_submit():
        payload = {
            "id_tipo_innovacion": form.tipo_innovacion.data,
            "id_foco_innovacion": form.foco_innovacion.data,
            "titulo": form.titulo.data,
            "descripcion": form.descripcion.data,
            "palabras_claves": form.palabras_claves.data,
            "recursos_requeridos": form.recursos_requeridos.data,
            "archivo_multimedia": None,
            "creador_por": session.get("user_email"),
            "estado": True
        }

        response = oportunidad_client.insert_data(payload)
        if response and response.get("estado") == 201:
            flash("Oportunidad creada exitosamente", "success")
            return redirect(url_for("vistaOportunidad.list_oportunidades"))
        else:
            flash("Error al crear la oportunidad", "danger")

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

    form = OportunidadForm(data=oportunidad[0])
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
            "creador_por": oportunidad[0].get("creador_por"),
            "estado": oportunidad[0].get("estado")
        }

        response = oportunidad_client.update_by_key("codigo_oportunidad", codigo_oportunidad, payload)
        if response and response.get("estado") == 200:
            flash("Oportunidad actualizada correctamente", "success")
            return redirect(url_for("vistaOportunidad.list_oportunidades"))
        else:
            flash("Error al actualizar la oportunidad", "danger")

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
