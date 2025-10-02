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
    template_folder="../templates/soluciones",
    url_prefix="/soluciones"
)


@soluciones_bp.route("/", methods=["GET"])
@login_required
def list_soluciones():
    """
    Lista soluciones con filtros (tipo_innovacion, foco_innovacion, estado).
    Usa SolucionService para obtener y enriquecer los datos.
    """
    # --- autenticación: preferimos current_user (Flask-Login) y fallback a session ---
    user_email = None
    try:
        if getattr(current_user, "is_authenticated", False):
            # Ajusta el atributo según tu User model (email, username, etc.)
            user_email = getattr(current_user, "email", None)
        if not user_email:
            user_email = session.get("user_email")
    except Exception:
        # Si algo inesperado falla con current_user, fallback a session
        user_email = session.get("user_email")

    if not user_email:
        flash("Debes iniciar sesión para ver las soluciones.", "warning")
        # Ajusta 'auth.login' por el endpoint real de login en tu app Flask
        return redirect(url_for("auth.login"))

    # --- leer filtros desde query params ---
    selected_tipo = request.args.get("tipo_innovacion", "").strip()
    selected_foco = request.args.get("foco_innovacion", "").strip()
    selected_estado = request.args.get("estado", "").strip()

    filters = {
        "id_tipo_innovacion": selected_tipo,
        "id_foco_innovacion": selected_foco,
        "estado": selected_estado
    }

    try:
        soluciones = SolucionService.list_solutions(filters)
        if not soluciones:
            flash("No hay soluciones disponibles.", "info")
        else:
            flash(f"Se obtuvieron {len(soluciones)} soluciones.", "success")
    except Exception as e:
        current_app.logger.exception("Error al obtener soluciones")
        flash(f"Error al obtener las soluciones: {e}", "danger")
        soluciones = []

    # --- obtener lista completa de focos y tipos para los selects de filtro (si quieres mostrarlos) ---
    try:
        focos = FocoInnovacionAPI.get_focos()
    except Exception:
        focos = []

    try:
        tipos = TipoInnovacionAPI.get_tipos()
    except Exception:
        tipos = []

    # --- verificar rol (perfil) para saber si es 'experto' ---
    perfil_client = APIClient(table_name="perfil")
    perfil_data = perfil_client.get_data(where_condition=f"usuario_email = '{user_email}'")
    is_experto = False
    try:
        if perfil_data and isinstance(perfil_data, list) and len(perfil_data) > 0:
            is_experto = str(perfil_data[0].get("rol", "")).lower() == "experto"
    except Exception:
        is_experto = False

    context = {
        "soluciones": soluciones,
        "tipos": tipos,
        "focos": focos,
        "selected_tipo": selected_tipo,
        "selected_foco": selected_foco,
        "selected_estado": selected_estado,
        "user_email": user_email,
        "is_experto": is_experto,
    }

    return render_template("soluciones/list_soluciones.html", **context)



# ===========================
# GET - Get solution by ID
# ===========================
"""@soluciones_bp.route("/<int:solucion_id>", methods=["GET"])
@login_required
def get_solution(solucion_id):
    solution = solucion_service.get(solucion_id)
    if not solution:
        flash("Solution not found", "error")
        return redirect(url_for("solucion.list_solutions"))
    return render_template("soluciones/detail.html", solution=solution)


# ===========================
# POST - Create a new solution
# ===========================
@soluciones_bp.route("/create", methods=["GET", "POST"])
@login_required
def create_solucion():
    form = SolucionForm()

    # Aquí deberías llenar dinámicamente los choices desde la API si es necesario
    form.tipo.choices = [(1, "Tipo A"), (2, "Tipo B")]
    form.foco.choices = [(1, "Foco A"), (2, "Foco B")]

    if form.validate_on_submit():
        response = service.crear_solucion(form, current_user.id)
        if response and response.status_code == 201:
            flash("Solución creada exitosamente", "success")
            return redirect(url_for("vistaSolucion.list_soluciones"))
        else:
            flash("Error al crear la solución", "danger")

    return render_template("soluciones/create.html", form=form)


# ===========================
# POST - Update a solution
# ===========================
@soluciones_bp.route("/update/<int:solucion_id>", methods=["GET", "POST"])
@login_required
def update_solution(solucion_id):
    solution = solucion_service.get(solucion_id)
    if not solution:
        flash("Solution not found", "error")
        return redirect(url_for("solucion.list_solutions"))

    if request.method == "POST":
        data = {
            "titulo": request.form.get("titulo"),
            "descripcion": request.form.get("descripcion"),
        }
        solucion_service.update(solucion_id, data)
        flash("Solution updated successfully", "success")
        return redirect(url_for("solucion.list_solutions"))

    return render_template("soluciones/update.html", solution=solution)


# ===========================
# POST - Delete a solution
# ===========================
@soluciones_bp.route("/delete/<int:solucion_id>", methods=["POST"])
@login_required
def delete_solution(solucion_id):
    solucion_service.delete(solucion_id)
    flash("Solution deleted successfully", "success")
    return redirect(url_for("solucion.list_solutions"))
"""