from flask import Blueprint, render_template, session, redirect, url_for, flash
from flask_login import current_user, login_required
from utils.api_client import APIClient
from config_flask import API_CONFIG
from datetime import datetime

dashboard_bp = Blueprint('dashboard', __name__)
api_client = APIClient(API_CONFIG['base_url'])

@dashboard_bp.route('/dashboard')
@login_required
def index():
    print('Accediendo al dashboard...')
    print(f'Contenido actual de la sesión: {dict(session)}')
    # Usar current_user para obtener el email autenticado
    user_email = getattr(current_user, 'email', None)
    if not user_email:
        print('No se encontró usuario autenticado')
        return redirect(url_for('login.login_view'))
    try:
        # Verificar si la sesión está activa
        if not session.get('user_email'):
            return redirect(url_for('login.login_view'))

        # Obtener datos del usuario autenticado
        user_data = {
            'email': user_email,
            'name': getattr(current_user, 'name', 'Usuario'),
            'role': getattr(current_user, 'role', 'Usuario')
        }
        
        # Inicializar contadores
        total_ideas = 0
        total_opportunities = 0
        total_projects = 0
        recent_activities = []
        
        # Obtener datos del API en paralelo
        try:
            # Ideas
            ideas = api_client.get_ideas()
            if ideas:
                total_ideas = len(ideas)
                # Agregar ideas recientes a las actividades
                for idea in ideas[:5]:
                    recent_activities.append({
                        'type': 'idea',
                        'title': idea.get('titulo', 'Sin título'),
                        'date': idea.get('fecha_creacion', '')
                    })
        except Exception as e:
            print(f'Error al obtener ideas: {e}')
        
        try:
            # Oportunidades
            oportunidades = api_client.get_oportunidades() or []
            if oportunidades:
                total_opportunities = len(oportunidades)
                # Agregar oportunidades recientes
                for oportunidad in oportunidades[:5]:
                    recent_activities.append({
                        'type': 'oportunidad',
                        'title': oportunidad.get('titulo', 'Sin título'),
                        'date': oportunidad.get('fecha_creacion', '')
                    })
        except Exception as e:
            print(f'Error al obtener oportunidades: {e}')
            
        try:
            # Soluciones
            soluciones = api_client.get_soluciones()
            if soluciones:
                total_projects = len(soluciones)
                # Agregar soluciones recientes
                for solucion in soluciones[:5]:
                    recent_activities.append({
                        'type': 'solucion',
                        'title': solucion.get('titulo', 'Sin título'),
                        'date': solucion.get('fecha_creacion', '')
                    })
        except Exception as e:
            print(f'Error al obtener soluciones: {e}')
            
        # Ordenar actividades recientes por fecha
        recent_activities.sort(key=lambda x: x['date'], reverse=True)
        recent_activities = recent_activities[:10]  # Mostrar solo las 10 más recientes
        
        return render_template('dashboard.html', 
                             user=user_data,
                             total_ideas=total_ideas,
                             total_opportunities=total_opportunities,
                             total_projects=total_projects,
                             recent_activities=recent_activities,
                             ideas_count=total_ideas,
                             oportunidades_count=total_opportunities,
                             solucion_count=total_projects,
                             now=datetime.now().strftime('%d/%m/%Y %H:%M:%S'))
    except Exception as e:
        print(f'Error al cargar el dashboard: {str(e)}')
        # En lugar de redirigir al login, mostramos el dashboard con datos básicos
        return render_template('dashboard.html',
                             user=user_data,
                             total_ideas=0,
                             total_opportunities=0,
                             total_projects=0,
                             recent_activities=[],
                             ideas_count=0,
                             oportunidades_count=0,
                             solucion_count=0,
                             now=datetime.now().strftime('%d/%m/%Y %H:%M:%S'),
                             error=str(e))
    
@dashboard_bp.route('/proyectos')
@login_required
def proyectos():
    # Lógica para cargar el dashboard
    return render_template('listar_proyectos.html')