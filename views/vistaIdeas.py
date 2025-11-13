# app/views/ideas.py - CORREGIDO
from flask import (
    Blueprint, render_template, request, redirect, url_for, flash, session, current_app
)
from flask_login import login_required
from datetime import datetime
from flask_wtf.csrf import CSRFProtect
from werkzeug.utils import secure_filename
from utils.api_client import APIClient
from forms.formsIdea import IdeaForm
import os
from collections import Counter

ideas_bp = Blueprint(
    "ideas",
    __name__,
    template_folder="templates",
    url_prefix="/ideas"
)

idea_client = APIClient("idea")

UPLOAD_FOLDER = os.path.join("static", "uploads")
os.makedirs(UPLOAD_FOLDER, exist_ok=True)



@ideas_bp.route('/', methods=['GET'])
def list_ideas():
    """Vista para listar ideas con filtros por tipo, foco y estado."""

    # Inicializar clientes para las APIs
    idea_client = APIClient('idea')
    tipo_client = APIClient('tipo_innovacion')
    foco_client = APIClient('foco_innovacion')

    # --- Obtener filtros desde la URL ---
    tipo_innovacion = request.args.get('tipo_innovacion')
    foco_innovacion = request.args.get('foco_innovacion')
    estado = request.args.get('estado')

    try:
        # --- Obtener datos desde la API ---
        ideas = idea_client.get_all() or []
        tipos = tipo_client.get_all() or []
        focos = foco_client.get_all() or []
        
        # 🔍 DEBUG: Ver qué datos llegan
        print("=" * 80)
        print("📊 DEBUG - TIPOS DE INNOVACIÓN:")
        if tipos:
            print(f"   Total tipos: {len(tipos)}")
            print(f"   Primer tipo: {tipos[0]}")
        else:
            print("   ⚠️ No hay tipos")
            
        print("\n📊 DEBUG - FOCOS DE INNOVACIÓN:")
        if focos:
            print(f"   Total focos: {len(focos)}")
            print(f"   Primer foco: {focos[0]}")
        else:
            print("   ⚠️ No hay focos")
            
        print("\n📊 DEBUG - IDEAS:")
        if ideas:
            print(f"   Total ideas: {len(ideas)}")
            print(f"   Primera idea: {ideas[0]}")
        else:
            print("   ⚠️ No hay ideas")
        print("=" * 80)
        
    except Exception as e:
        flash(f"Ocurrió un error al obtener los datos: {e}", "danger")
        ideas, tipos, focos = [], [], []

    # --- Crear diccionarios para mapear nombres ---
    tipo_dict = {t.get('id_tipo_innovacion'): t.get('name', '') for t in tipos}
    foco_dict = {f.get('id_foco_innovacion'): f.get('name', '') for f in focos}
    
    # 🔍 DEBUG: Ver los diccionarios creados
    print("\n📖 DEBUG - DICCIONARIOS:")
    print(f"   tipo_dict: {tipo_dict}")
    print(f"   foco_dict: {foco_dict}")

    # --- Aplicar filtros ---
    if tipo_innovacion:
        ideas = [i for i in ideas if str(i.get('id_tipo_innovacion')) == tipo_innovacion]

    if foco_innovacion:
        ideas = [i for i in ideas if str(i.get('id_foco_innovacion')) == foco_innovacion]

    if estado in ['0', '1']:
        estado_bool = estado == '1'
        ideas = [i for i in ideas if i.get('estado') == estado_bool]

    # --- Renderizar plantilla ---
    return render_template(
        'list_ideas.html',
        ideas=ideas,
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

@ideas_bp.route("/<int:codigo_idea>", methods=["GET"])
@login_required
def get_idea(codigo_idea):
    """Vista para ver detalles de una idea con tipo y foco de innovación"""
    
    # Obtener la idea
    idea = idea_client.get_by_key("codigo_idea", codigo_idea)
    
    # Validación robusta
    if not idea or not isinstance(idea, list) or len(idea) == 0:
        flash("Idea no encontrada", "error")
        return redirect(url_for("ideas.list_ideas"))
    
    # Trabajar con los datos de la idea
    idea_data = idea[0]
    
    # Enriquecer con nombres de tipo y foco
    try:
        # Obtener catálogos
        tipos = idea_client.fetch_endpoint_data("tipo_innovacion") or []
        focos = idea_client.fetch_endpoint_data("foco_innovacion") or []
        
        # Crear mapeos ID → Nombre
        tipo_dict = {t.get('id_tipo_innovacion'): t.get('name', 'No especificado') for t in tipos}
        foco_dict = {f.get('id_foco_innovacion'): f.get('name', 'No especificado') for f in focos}
        
        # Agregar los nombres a la idea
        id_tipo = idea_data.get('id_tipo_innovacion')
        id_foco = idea_data.get('id_foco_innovacion')
        
        idea_data['tipo_innovacion_nombre'] = tipo_dict.get(id_tipo, 'No especificado')
        idea_data['foco_innovacion_nombre'] = foco_dict.get(id_foco, 'No especificado')
        
    except Exception as e:
        current_app.logger.exception(f"Error al cargar tipo/foco: {e}")
        # Si falla, usar valores por defecto
        idea_data['tipo_innovacion_nombre'] = 'No especificado'
        idea_data['foco_innovacion_nombre'] = 'No especificado'
    
    return render_template("detail_ideas.html", idea=idea_data)


@ideas_bp.route("/update/<int:codigo_idea>", methods=["GET", "POST"])
@login_required
def update_idea(codigo_idea):
    solution = idea_client.get_by_key("codigo_idea", codigo_idea)
    
    if not solution or len(solution) == 0:
        flash("Idea no encontrada", "error")
        return redirect(url_for("ideas.list_ideas"))

    # ✅ Trabajar con una copia para no modificar el original
    idea_data = solution[0].copy()
    
    # ✅ Convertir fecha_creacion a datetime si viene como string
    if isinstance(idea_data.get("fecha_creacion"), str):
        try:
            fecha_str = idea_data["fecha_creacion"]
            # Intentar diferentes formatos
            for fmt in ["%Y-%m-%d", "%Y-%m-%dT%H:%M:%S", "%d/%m/%Y"]:
                try:
                    idea_data["fecha_creacion"] = datetime.strptime(fecha_str, fmt)
                    break
                except ValueError:
                    continue
        except Exception as e:
            current_app.logger.warning(f"Error al convertir fecha: {e}")
            idea_data["fecha_creacion"] = datetime.now()
    
    # Cargar opciones dinámicas desde la API
    try:
        focos_tipos = {
            "focos": idea_client.fetch_endpoint_data("foco_innovacion"),
            "tipos": idea_client.fetch_endpoint_data("tipo_innovacion")
        }
    except Exception as e:
        current_app.logger.exception("Error al cargar opciones dinámicas")
        focos_tipos = {
            "focos": [],
            "tipos": []
        }

    # ✅ Crear formulario con idea_data (que ya tiene la fecha convertida)
    form = IdeaForm(data=idea_data)
    form.id_foco_innovacion.choices = [(f['id_foco_innovacion'], f['name']) for f in focos_tipos['focos']]
    form.id_tipo_innovacion.choices = [(t['id_tipo_innovacion'], t['name']) for t in focos_tipos['tipos']]

    if request.method == "POST" and form.validate_on_submit():
        payload = {
            "id_tipo_innovacion": form.id_tipo_innovacion.data,
            "id_foco_innovacion": form.id_foco_innovacion.data,
            "titulo": form.titulo.data,
            "descripcion": form.descripcion.data,
            "palabras_claves": form.palabras_claves.data,
            "recursos_requeridos": form.recursos_requeridos.data,
            "fecha_creacion": form.fecha_creacion.data.strftime("%Y-%m-%d"),
            "archivo_multimedia": solution[0].get("archivo_multimedia"),
            "creador_por": solution[0].get("creador_por"),
            "estado": form.estado.data  # ✅ CAMBIO AQUÍ: Usar el valor del formulario
        }

        response = idea_client.update_by_key("codigo_idea", codigo_idea, payload)

        if response and response.get("estado") == 200:
            flash("Idea actualizada correctamente", "success")
            return redirect(url_for("ideas.list_ideas"))
        else:
            flash("Error al actualizar la idea", "error")

    return render_template("update_ideas.html", form=form, idea=idea_data)



@ideas_bp.route("/delete/<int:codigo_idea>", methods=["POST"])
@login_required
def delete_idea(codigo_idea):
    try:
        current_app.logger.info(f"🗑️ Intentando eliminar idea {codigo_idea}")
        
        # Verificar que existe antes de eliminar
        idea = idea_client.get_by_key("codigo_idea", codigo_idea)
        
        if not idea or len(idea) == 0:
            current_app.logger.warning(f"⚠️ Idea {codigo_idea} no encontrada")
            flash("Idea no encontrada", "error")
            return redirect(url_for("ideas.list_ideas"))
        
        current_app.logger.info(f"✅ Idea encontrada, procediendo a eliminar")
        
        # Intentar eliminar
        response = idea_client.delete_by_key("codigo_idea", codigo_idea)
        
        current_app.logger.info(f"📤 Respuesta: {response}")
        
        # Validar respuesta
        if response:
            estado = response.get("estado") or response.get("status_code") or response.get("status")
            current_app.logger.info(f"📊 Estado: {estado}")
            
            if estado in (200, 204):
                flash("✅ Idea eliminada correctamente", "success")
            else:
                error_msg = response.get("mensaje") or response.get("message") or "Error desconocido"
                flash(f"Error al eliminar: {error_msg}", "error")
        else:
            flash("Error: Sin respuesta del servidor", "error")
            
    except Exception as e:
        current_app.logger.exception(f"❌ Excepción: {e}")
        flash(f"Error al eliminar la idea: {str(e)}", "danger")
    
    return redirect(url_for("ideas.list_ideas"))

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

    # Cargar focos y tipos
    try:
        focos = idea_client.fetch_endpoint_data("foco_innovacion")
        tipos = idea_client.fetch_endpoint_data("tipo_innovacion")
        form.id_foco_innovacion.choices = [(f["id_foco_innovacion"], f["name"]) for f in focos]
        form.id_tipo_innovacion.choices = [(t["id_tipo_innovacion"], t["name"]) for t in tipos]
    except Exception as e:
        current_app.logger.exception("Error al cargar focos/tipos")
        flash("Error al cargar focos o tipos de innovación", "danger")
        form.id_foco_innovacion.choices = []
        form.id_tipo_innovacion.choices = []

    if form.validate_on_submit():
        # Guardar archivo
        archivo_url = ""
        if form.archivo_multimedia.data:
            archivo = form.archivo_multimedia.data
            filename = secure_filename(archivo.filename)
            path = os.path.join(UPLOAD_FOLDER, filename)
            try:
                archivo.save(path)
                archivo_url = f"/{path}"
            except Exception as e:
                current_app.logger.exception("Error al guardar archivo")
                flash("Error al guardar el archivo.", "danger")

        fecha_creacion = form.fecha_creacion.data if form.fecha_creacion.data else datetime.now()
        
        payload = {
            "id_tipo_innovacion": int(form.id_tipo_innovacion.data),
            "id_foco_innovacion": int(form.id_foco_innovacion.data),
            "titulo": str(form.titulo.data).strip(),
            "descripcion": str(form.descripcion.data).strip(),
            "fecha_creacion": fecha_creacion.strftime("%Y-%m-%dT%H:%M:%S"),
            "palabras_claves": str(form.palabras_claves.data).strip(),
            "recursos_requeridos": int(form.recursos_requeridos.data),
            "archivo_multimedia": archivo_url,
            "creador_por": session.get("user_email", ""),
            "estado": True
        }

        try:
            response = idea_client.insert_data(payload)

            if isinstance(response, dict):
                estado = response.get("estado") or response.get("status")
                mensaje = response.get("mensaje") or response.get("message") or str(response)

                if estado in (200, 201) or "creada" in mensaje.lower() or "success" in mensaje.lower():
                    flash("Idea creada exitosamente ✅", "success")
                    return redirect(url_for("ideas.list_ideas"))
                else:
                    error_detail = response.get("error") or response.get("detail") or mensaje
                    flash(f"Error al crear la idea: {error_detail}", "danger")

            elif hasattr(response, "status_code"):
                if response.status_code in (200, 201):
                    flash("Idea creada exitosamente ✅", "success")
                    return redirect(url_for("ideas.list_ideas"))
                else:
                    flash(f"Error HTTP {response.status_code} al crear la idea.", "danger")

            elif response is None:
                flash("Error de conexión con el servidor.", "danger")
            else:
                flash("Respuesta inesperada del servidor.", "danger")

        except Exception as e:
            current_app.logger.exception("Error al crear idea")
            flash("Error al guardar la idea en el servidor", "danger")

    elif request.method == "POST":
        for field, errors in form.errors.items():
            for error in errors:
                flash(f"Error en {field}: {error}", "danger")

    return render_template("create_ideas.html", form=form)


# Secciones extra
@ideas_bp.route('/matriz-evaluacion')
def matriz_evaluacion():
    return render_template('templatesIdeas/matriz_evaluacion.html')


@ideas_bp.route('/estadisticas', methods=['GET'])
@login_required
def estadisticas():
    try:
        ideas = idea_client.get_all() or []
        tipos = idea_client.fetch_endpoint_data("tipo_innovacion") or []
        focos = idea_client.fetch_endpoint_data("foco_innovacion") or []

        # === Mapas de IDs a nombres ===
        tipo_map = {
            t.get("id_tipo_innovacion"): (
                t.get("name") or t.get("nombre") or t.get("tipo") or str(t.get("id_tipo_innovacion"))
            )
            for t in tipos if t.get("id_tipo_innovacion") is not None
        }

        foco_map = {
            f.get("id_foco_innovacion"): (
                f.get("name") or f.get("nombre") or f.get("foco") or str(f.get("id_foco_innovacion"))
            )
            for f in focos if f.get("id_foco_innovacion") is not None
        }

        # === Funciones auxiliares ===
        def tipo_label(idea):
            for k in ("tipo_innovacion", "tipo_nombre", "tipo", "tipo_name"):
                v = idea.get(k)
                if v:
                    return str(v)
            tid = idea.get("id_tipo_innovacion")
            return tipo_map.get(tid, "Desconocido")

        def foco_label(idea):
            for k in ("foco_innovacion", "foco_nombre", "foco", "foco_name"):
                v = idea.get(k)
                if v:
                    return str(v)
            fid = idea.get("id_foco_innovacion")
            return foco_map.get(fid, "Desconocido")

        def is_aprobada(idea):
            e = idea.get("estado")
            if isinstance(e, bool):
                return e
            if isinstance(e, (int, float)):
                return int(e) == 1
            if isinstance(e, str):
                return e.lower() in ("aprobada", "aprobado", "true", "1", "si", "sí", "approved")
            return False

        # === Cálculos principales ===
        total_ideas = len(ideas)
        ideas_aprobadas = sum(1 for i in ideas if is_aprobada(i))
        ideas_pendientes = total_ideas - ideas_aprobadas

        por_tipo = Counter(tipo_label(i) for i in ideas)
        por_foco = Counter(foco_label(i) for i in ideas)

        ideas_por_tipo = sorted(por_tipo.items(), key=lambda x: x[1], reverse=True)
        ideas_por_foco = sorted(por_foco.items(), key=lambda x: x[1], reverse=True)

        creador_key_candidates = lambda idea: (
            idea.get("creador_por") or idea.get("usuario") or idea.get("autor") or idea.get("user_email")
        )
        top_generadores = Counter(creador_key_candidates(i) or "Anónimo" for i in ideas).most_common(10)

        # === Renderizar la plantilla ===
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
        import traceback
        print("🚨 ERROR EN /ideas/estadisticas 🚨")
        print(traceback.format_exc())
        current_app.logger.exception(f"Error al generar estadísticas de ideas: {e}")

        flash(f"Error al generar estadísticas: {e}", "danger")

        print("📊 DEBUG ideas:", ideas)


        # No redirige al listar — se queda en la misma página mostrando vacíos
        return render_template("estadisticas_ideas.html",
            total_ideas=total_ideas,
            ideas_aprobadas=ideas_aprobadas,
            ideas_pendientes=ideas_pendientes,
            ideas_por_tipo=ideas_por_tipo,
            ideas_por_foco=ideas_por_foco,
            top_generadores=top_generadores
        )



@ideas_bp.route("/retos", methods=["GET"])
@login_required
def retos():
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


@ideas_bp.route("/evaluacion", methods=["GET"])
@login_required
def evaluacion():
    try:
        ideas = idea_client.get_all() or []

        ideas_pendientes = []
        for idea in ideas:
            estado = idea.get("estado")
            aprobada = False
            if isinstance(estado, bool):
                aprobada = estado
            elif isinstance(estado, (int, float)):
                aprobada = int(estado) == 1
            elif isinstance(estado, str):
                aprobada = estado.lower() in ("aprobada", "aprobado", "approved", "true", "1", "si", "sí")

            if not aprobada:
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
    """Mercado de ideas - solo muestra ideas aprobadas"""
    try:
        ideas_mercado = idea_client.get_all() or []
        
        # ✅ FILTRAR SOLO APROBADAS (estado = True)
        ideas_mercado = [i for i in ideas_mercado if i.get('estado') == True]
        
        focos_tipos = {
            "focos": idea_client.fetch_endpoint_data("foco_innovacion"),
            "tipos": idea_client.fetch_endpoint_data("tipo_innovacion")
        }
        
        foco_map = {f['id_foco_innovacion']: f['name'] for f in focos_tipos['focos']}
        tipo_map = {t['id_tipo_innovacion']: t['name'] for t in focos_tipos['tipos']}
        
        for idea in ideas_mercado:
            idea['foco_innovacion_nombre'] = foco_map.get(idea['id_foco_innovacion'], 'Desconocido')
            idea['tipo_innovacion_nombre'] = tipo_map.get(idea['id_tipo_innovacion'], 'Desconocido')
            
            fecha = idea.get("fecha_creacion")
            if isinstance(fecha, str):
                try:
                    idea["fecha_creacion"] = datetime.strptime(fecha[:10], "%Y-%m-%d")
                except Exception:
                    idea["fecha_creacion"] = None
            elif fecha is None:
                idea["fecha_creacion"] = None
                
    except Exception as e:
        current_app.logger.exception("Error al obtener ideas para el mercado")
        flash(f"Error al obtener ideas del mercado: {e}", "danger")
        ideas_mercado = []
    
    return render_template(
        "mercado_ideas.html",
        ideas_mercado=ideas_mercado
    )