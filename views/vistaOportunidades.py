from flask import Blueprint, render_template, request, redirect, url_for, flash, session, current_app
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
        # Validar que cada oportunidad tiene el atributo 'codigo_oportunidad'
        for oportunidad in oportunidades:
            if "codigo_oportunidad" not in oportunidad:
                current_app.logger.warning("La oportunidad no tiene 'codigo_oportunidad': %s", oportunidad)
        form = OportunidadForm()
    except Exception as e:
        current_app.logger.exception("Error al obtener oportunidades")
        flash(f"Error al obtener las oportunidades: {e}", "danger")
        oportunidades = []
        form = OportunidadForm()

    return render_template("list_oportunidades.html", oportunidades=oportunidades, form=form)



@oportunidades_bp.route("/<int:codigo_oportunidad>", methods=["GET"])
@login_required
def view_oportunidad(codigo_oportunidad):
    oportunidad = oportunidad_client.get_by_id("codigo_oportunidad", codigo_oportunidad)
    if not oportunidad:
        flash("Oportunidad no encontrada", "error")
        return redirect(url_for("vistaOportunidad.list_oportunidades"))

    form = OportunidadForm(data=oportunidad[0])

    return render_template("view_oportunidades.html", oportunidad=oportunidad[0], form=form)

@oportunidades_bp.route("/create", methods=["GET", "POST"])
@login_required
def create_oportunidad():
    form = OportunidadForm()

    # Load dynamic choices for the form
    focos = oportunidad_client.get_all("foco_innovacion")
    tipos = oportunidad_client.get_all("tipo_innovacion")
    form.load_dynamic_choices(focos, tipos)

    if form.validate_on_submit():
        payload = {
            "titulo": form.titulo.data,
            "descripcion": form.descripcion.data,
            "palabras_claves": form.palabras_claves.data,
            "recursos_requeridos": form.recursos_requeridos.data,
            "fecha_creacion": form.fecha_creacion.data.strftime('%Y-%m-%d') if form.fecha_creacion.data else None,
            "archivo_multimedia": form.archivo_multimedia.data.filename,
            "creador_por": session.get("user_email"),
            "id_foco_innovacion": form.id_foco_innovacion.data,
            "id_tipo_innovacion": form.id_tipo_innovacion.data,
            "estado": form.estado.data,
        }

        response = oportunidad_client.insert_data(payload)
        if response and response.status_code == 201:
            flash("Oportunidad creada exitosamente", "success")
            return redirect(url_for("vistaOportunidad.list_oportunidades"))
        else:
            flash("Error al crear la oportunidad", "danger")

    return render_template("create_oportunidades.html", form=form)

@oportunidades_bp.route("/update/<int:codigo_oportunidad>", methods=["GET", "POST"])
@login_required
def update_oportunidad(codigo_oportunidad):
    oportunidad = oportunidad_client.get_by_id("codigo_oportunidad", codigo_oportunidad)
    if not oportunidad:
        flash("Oportunidad no encontrada", "error")
        return redirect(url_for("vistaOportunidad.list_oportunidades"))

    if isinstance(oportunidad[0].get("fecha_creacion"), str):
        try:
            oportunidad[0]["fecha_creacion"] = datetime.strptime(oportunidad[0]["fecha_creacion"], "%Y-%m-%d")
        except ValueError:
            flash("Formato de fecha inválido en la oportunidad", "danger")
            return redirect(url_for("vistaOportunidad.list_oportunidades"))

    form = OportunidadForm(data=oportunidad[0])

    # Load dynamic choices for the form
    focos = oportunidad_client.get_all("foco_innovacion")
    tipos = oportunidad_client.get_all("tipo_innovacion")
    form.load_dynamic_choices(focos, tipos)

    if request.method == "POST" and form.validate_on_submit():
        payload = {
            "titulo": form.titulo.data,
            "descripcion": form.descripcion.data,
            "palabras_claves": form.palabras_claves.data,
            "recursos_requeridos": form.recursos_requeridos.data,
            "fecha_creacion": form.fecha_creacion.data.strftime('%Y-%m-%d') if form.fecha_creacion.data else None,
            "archivo_multimedia": form.archivo_multimedia.data.filename,
            "id_foco_innovacion": form.id_foco_innovacion.data,
            "id_tipo_innovacion": form.id_tipo_innovacion.data,
            "estado": form.estado.data,
        }
        oportunidad_client.update_data(codigo_oportunidad, payload)
        flash("Oportunidad actualizada correctamente", "success")
        return redirect(url_for("vistaOportunidad.list_oportunidades"))

    return render_template("edit_oportunidades.html", form=form, oportunidad=oportunidad[0])

@oportunidades_bp.route("/delete/<int:codigo_oportunidad>", methods=["POST"])
@login_required
def delete_oportunidad(codigo_oportunidad):
    oportunidad = oportunidad_client.get_by_id("codigo_oportunidad", codigo_oportunidad)
    if not oportunidad:
        flash("Oportunidad no encontrada", "error")
        return redirect(url_for("vistaOportunidad.list_oportunidades"))

    oportunidad_client.delete_data(codigo_oportunidad)
    flash("Oportunidad eliminada correctamente", "success")
    return redirect(url_for("vistaOportunidad.list_oportunidades"))

@oportunidades_bp.route("/confirmar/<int:codigo_oportunidad>", methods=["POST"])
@login_required
def confirmar_oportunidad(codigo_oportunidad):
    oportunidad = oportunidad_client.get_by_id("codigo_oportunidad", codigo_oportunidad)
    if not oportunidad:
        flash("Oportunidad no encontrada", "error")
        return redirect(url_for("vistaOportunidad.list_oportunidades"))

    oportunidad_client.confirm("codigo_oportunidad", codigo_oportunidad)
    flash("Oportunidad confirmada exitosamente", "success")
    return redirect(url_for("vistaOportunidad.list_oportunidades"))
