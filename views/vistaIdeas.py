# app/views/ideas.py
from flask import (
    Blueprint, render_template, request, redirect, url_for, flash, session, current_app
)
from flask_login import login_required
from datetime import datetime
from werkzeug.utils import secure_filename
from utils.api_client import APIClient
from forms.formsIdea import IdeaForm
import os

ideas_bp = Blueprint(
    "ideas",
    __name__,
    template_folder="templates",
    url_prefix="/ideas"
)

idea_client = APIClient("idea")

UPLOAD_FOLDER = os.path.join("static", "uploads")
os.makedirs(UPLOAD_FOLDER, exist_ok=True)


@ideas_bp.route("/", methods=["GET"])
@login_required
def list_ideas():
    try:
        ideas = idea_client.get_all()
        focos = idea_client.fetch_endpoint_data("foco_innovacion")
        tipos = idea_client.fetch_endpoint_data("tipo_innovacion")

        form = IdeaForm()
        form.load_dynamic_choices(focos, tipos)

    except Exception as e:
        current_app.logger.exception("Error al obtener ideas")
        flash(f"Error al obtener las ideas: {e}", "danger")
        ideas, focos, tipos = [], [], []
        form = IdeaForm()

    return render_template("list_ideas.html", ideas=ideas, focos=focos, tipos=tipos, form=form)


@ideas_bp.route("/<int:codigo_idea>", methods=["GET"])
@login_required
def get_idea(codigo_idea):
    idea = idea_client.get_by_id("codigo_idea", codigo_idea)
    if not idea:
        flash("Idea no encontrada", "error")
        return redirect(url_for("ideas.list_ideas"))
    return render_template("detail_ideas.html", idea=idea[0])


@ideas_bp.route("/update/<int:codigo_idea>", methods=["GET", "POST"])
@login_required
def update_idea(codigo_idea):
    idea = idea_client.get_by_id("codigo_idea", codigo_idea)
    if not idea:
        flash("Idea no encontrada", "error")
        return redirect(url_for("ideas.list_ideas"))

    if isinstance(idea[0].get("fecha_creacion"), str):
        try:
            idea[0]["fecha_creacion"] = datetime.strptime(idea[0]["fecha_creacion"], "%Y-%m-%d")
        except ValueError:
            flash("Formato de fecha inválido", "danger")
            return redirect(url_for("ideas.list_ideas"))

    form = IdeaForm(data=idea[0])

    if request.method == "POST" and form.validate_on_submit():
        payload = {
            "id_tipo_innovacion": form.id_tipo_innovacion.data,
            "id_foco_innovacion": form.id_foco_innovacion.data,
            "titulo": form.titulo.data,
            "descripcion": form.descripcion.data,
            "palabras_claves": form.palabras_claves.data,
            "recursos_requeridos": form.recursos_requeridos.data,
            "fecha_creacion": form.fecha_creacion.data.strftime("%Y-%m-%d")
        }
        idea_client.update("codigo_idea", codigo_idea, payload)
        flash("Idea actualizada correctamente", "success")
        return redirect(url_for("ideas.list_ideas"))

    return render_template("update_ideas.html", form=form, idea=idea[0])


@ideas_bp.route("/delete/<int:codigo_idea>", methods=["GET", "POST"])
@login_required
def delete_idea(codigo_idea):
    idea = idea_client.get_by_id("codigo_idea", codigo_idea)
    if not idea:
        flash("Idea no encontrada", "error")
        return redirect(url_for("ideas.list_ideas"))

    if request.method == "POST":
        idea_client.delete("codigo_idea", codigo_idea)
        flash("Idea eliminada correctamente", "success")
        return redirect(url_for("ideas.list_ideas"))

    return render_template("delete_ideas.html", idea=idea[0])


@ideas_bp.route("/confirmar/<int:codigo_idea>", methods=["GET", "POST"])
@login_required
def confirmar_idea(codigo_idea):
    idea = idea_client.get_by_id("codigo_idea", codigo_idea)
    if not idea:
        flash("Idea no encontrada", "error")
        return redirect(url_for("ideas.list_ideas"))

    if request.method == "POST" and request.form.get("confirmar"):
        idea_client.confirm("codigo_idea", codigo_idea)
        flash("Idea confirmada exitosamente", "success")
        return redirect(url_for("ideas.list_ideas"))

    return render_template("confirmar_ideas.html", idea=idea[0])


@ideas_bp.route("/create", methods=["GET", "POST"])
@login_required
def create_idea():
    form = IdeaForm()

    try:
        focos = idea_client.fetch_endpoint_data("foco_innovacion")
        tipos = idea_client.fetch_endpoint_data("tipo_innovacion")
        form.id_foco_innovacion.choices = [(f["id_foco_innovacion"], f["name"]) for f in focos]
        form.id_tipo_innovacion.choices = [(t["id_tipo_innovacion"], t["name"]) for t in tipos]
    except Exception:
        flash("Error al cargar focos o tipos de innovación", "danger")
        form.id_foco_innovacion.choices = []
        form.id_tipo_innovacion.choices = []

    if form.validate_on_submit():
        archivo_url = None
        if form.archivo_multimedia.data:
            archivo = form.archivo_multimedia.data
            filename = secure_filename(archivo.filename)
            path = os.path.join(UPLOAD_FOLDER, filename)
            archivo.save(path)
            archivo_url = f"/{path}"

        payload = {
            "id_tipo_innovacion": form.id_tipo_innovacion.data,
            "id_foco_innovacion": form.id_foco_innovacion.data,
            "titulo": form.titulo.data,
            "descripcion": form.descripcion.data,
            "fecha_creacion": form.fecha_creacion.data.strftime("%Y-%m-%dT%H:%M:%S")
            if form.fecha_creacion.data else datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
            "palabras_claves": form.palabras_claves.data,
            "recursos_requeridos": form.recursos_requeridos.data,
            "archivo_multimedia": archivo_url,
            "creador_por": session.get("user_email"),
            "estado": True
        }

        response = idea_client.create(payload)
        if response and response.status_code == 201:
            flash("Idea creada exitosamente", "success")
            return redirect(url_for("ideas.list_ideas"))
        else:
            flash("Error al crear la idea", "danger")

    return render_template("create_ideas.html", form=form)


# Secciones extra
@ideas_bp.route('/matriz-evaluacion')
def matriz_evaluacion():
    return render_template('templatesIdeas/matriz_evaluacion.html')

@ideas_bp.route('/estadisticas', methods=['GET'])
@login_required
def estadisticas():
    """
    Genera las métricas que usa templatesIdeas/estadisticas.html:
    - total_ideas
    - ideas_aprobadas
    - ideas_pendientes
    - ideas_por_tipo (lista de tuplas (nombre_tipo, cantidad))
    - ideas_por_foco (lista de tuplas (nombre_foco, cantidad))
    """
    try:
        ideas = idea_client.get_all() or []
        tipos = idea_client.fetch_endpoint_data("tipo_innovacion") or []
        focos = idea_client.fetch_endpoint_data("foco_innovacion") or []

        # Construir mapas id -> nombre para tipos y focos (soportando distintas claves)
        tipo_map = {}
        for t in tipos:
            # claves probables: id_tipo_innovacion, id, id_tipo
            tid = t.get("id_tipo_innovacion") or t.get("id") or t.get("id_tipo")
            tname = t.get("name") or t.get("nombre") or t.get("tipo") or str(tid)
            if tid is not None:
                tipo_map[tid] = tname

        foco_map = {}
        for f in focos:
            fid = f.get("id_foco_innovacion") or f.get("id") or f.get("id_foco")
            fname = f.get("name") or f.get("nombre") or f.get("foco") or str(fid)
            if fid is not None:
                foco_map[fid] = fname

        
        def tipo_label(idea):
            
            for k in ("tipo_innovacion", "tipo_nombre", "tipo", "tipo_name"):
                v = idea.get(k)
                if v:
                    return str(v)
            
            tid = idea.get("id_tipo_innovacion") or idea.get("tipo_id") or idea.get("id_tipo")
            if tid is not None and tid in tipo_map:
                return tipo_map[tid]
            return "Desconocido"

        def foco_label(idea):
            for k in ("foco_innovacion", "foco_nombre", "foco", "foco_name"):
                v = idea.get(k)
                if v:
                    return str(v)
            fid = idea.get("id_foco_innovacion") or idea.get("foco_id") or idea.get("id_foco")
            if fid is not None and fid in foco_map:
                return foco_map[fid]
            return "Desconocido"

        
        def is_aprobada(idea):
            e = idea.get("estado")
            
            if isinstance(e, bool):
                return bool(e)
            if isinstance(e, (int, float)):
                return int(e) == 1
            if isinstance(e, str):
                return e.lower() in ("aprobada", "aprobado", "approved", "true", "1", "si", "sí")
            return False

        total_ideas = len(ideas)
        ideas_aprobadas = sum(1 for i in ideas if is_aprobada(i))
        ideas_pendientes = total_ideas - ideas_aprobadas

        # Agrupaciones
        por_tipo = Counter(tipo_label(i) for i in ideas)
        por_foco = Counter(foco_label(i) for i in ideas)

        # Convertir a listas ordenadas (nombre, cantidad)
        ideas_por_tipo = sorted(por_tipo.items(), key=lambda x: x[1], reverse=True)
        ideas_por_foco = sorted(por_foco.items(), key=lambda x: x[1], reverse=True)

        # Opcional: Top generadores (10 primeros)
        creador_key_candidates = lambda idea: idea.get("creador_por") or idea.get("usuario") or idea.get("autor") or idea.get("user_email")
        top_generadores = Counter(creador_key_candidates(i) or "Anónimo" for i in ideas).most_common(10)

        return render_template(
            "templatesIdeas/estadisticas.html",
            total_ideas=total_ideas,
            ideas_aprobadas=ideas_aprobadas,
            ideas_pendientes=ideas_pendientes,
            ideas_por_tipo=ideas_por_tipo,
            ideas_por_foco=ideas_por_foco,
            top_generadores=top_generadores  
        )

    except Exception as e:
        current_app.logger.exception("Error al generar estadísticas de ideas")
        flash(f"Error al generar estadísticas: {e}", "danger")
        return redirect(url_for("ideas.list_ideas"))


@ideas_bp.route("/retos", methods=["GET"])
@login_required
def retos():
    """
    Muestra los retos de innovación (ideas destacadas o seleccionadas como retos).
    """
    try:
       
        retos = idea_client.fetch_endpoint_data("retos")

        for r in retos:
            if isinstance(r.get("fecha_creacion"), str):
                try:
                    r["fecha_creacion"] = datetime.strptime(r["fecha_creacion"], "%Y-%m-%d")
                except Exception:
                    pass

    except Exception as e:
        current_app.logger.exception("Error al obtener retos")
        flash(f"Error al obtener los retos: {e}", "danger")
        retos = []

    
    return render_template("retos_ideas.html", retos=retos)


@ideas_bp.route('/top-generadores')
@login_required
def top_generadores():
    try:
        ideas = idea_client.get_all() or []
        creador_key_candidates = lambda idea: idea.get("creador_por") or idea.get("usuario") or idea.get("autor") or idea.get("user_email")
        top_generadores = Counter(creador_key_candidates(i) or "Anónimo" for i in ideas).most_common(10)
    except Exception:
        top_generadores = []

    return render_template("top_generadores.html", top_generadores=top_generadores)

from collections import Counter

@ideas_bp.route("/evaluacion", methods=["GET"])
@login_required
def evaluacion():
    """
    Muestra las ideas pendientes de evaluación.
    """
    try:
        # Obtener todas las ideas
        ideas = idea_client.get_all() or []

        ideas_pendientes = []
        for idea in ideas:
            # Solo ideas que no estén aprobadas
            estado = idea.get("estado")
            aprobada = False
            if isinstance(estado, bool):
                aprobada = estado
            elif isinstance(estado, (int, float)):
                aprobada = int(estado) == 1
            elif isinstance(estado, str):
                aprobada = estado.lower() in ("aprobada", "aprobado", "approved", "true", "1", "si", "sí")

            if not aprobada:
                # Convertir fecha a datetime si viene como string
                fecha = idea.get("fecha_creacion")
                if isinstance(fecha, str):
                    try:
                        idea["fecha_creacion"] = datetime.strptime(fecha[:10], "%Y-%m-%d")
                    except Exception:
                        idea["fecha_creacion"] = None
                ideas_pendientes.append(idea)

        return render_template("evaluacion.html", ideas_pendientes=ideas_pendientes)

    except Exception as e:
        current_app.logger.exception("Error al obtener ideas para evaluación")
        flash(f"Error al obtener ideas pendientes de evaluación: {e}", "danger")
        return render_template("evaluacion_ideas.html", ideas_pendientes=[])


@ideas_bp.route("/mercado", methods=["GET"])
@login_required
def mercado():
    """
    Muestra el mercado de ideas.
    Convierte la fecha de creación a datetime si viene como string para usar strftime en el template.
    """
    try:
        ideas_mercado = idea_client.get_all() or []

        for idea in ideas_mercado:
            fecha = idea.get("fecha_creacion")
            if isinstance(fecha, str):
                try:
                    idea["fecha_creacion"] = datetime.strptime(fecha[:10], "%Y-%m-%d")
                except Exception:
                    idea["fecha_creacion"] = None  # evita que falle strftime
            elif fecha is None:
                idea["fecha_creacion"] = None

    except Exception as e:
        current_app.logger.exception("Error al obtener ideas para el mercado")
        flash(f"Error al obtener ideas del mercado: {e}", "danger")
        ideas_mercado = []

    return render_template("mercado_ideas.html", ideas_mercado=ideas_mercado)


