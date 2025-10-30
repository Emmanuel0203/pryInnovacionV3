from flask import Blueprint, render_template, session, redirect, url_for, flash, current_app
from flask_login import current_user, login_required
from utils.api_client import APIClient
from config_flask import API_CONFIG, DASHBOARD_METAS
from datetime import datetime, timedelta

dashboard_bp = Blueprint('dashboard', __name__)


def parse_date(value):
    if not value:
        return None
    try:
        # Try ISO format first
        if isinstance(value, str):
            # Remove timezone info if present
            v = value.split('+')[0].split('Z')[0].strip()
            # If contains a space, take first part
            v = v.split(' ')[0]
            return datetime.fromisoformat(v)
        if isinstance(value, datetime):
            return value
    except Exception:
        try:
            return datetime.strptime(value, '%Y-%m-%d')
        except Exception:
            return None


def last_n_months_labels(n=6):
    # default: end at now
    end = datetime.now()
    # compute the earliest month (n-1 months before end)
    start_month = end.month - (n - 1)
    start_year = end.year
    # normalize start_month to be within 1..12
    while start_month <= 0:
        start_month += 12
        start_year -= 1

    labels = []
    months = []
    ym_year = start_year
    ym_month = start_month
    for _ in range(n):
        d = datetime(ym_year, ym_month, 1)
        labels.append(d.strftime('%b %Y'))
        months.append((ym_year, ym_month))
        # increment month
        ym_month += 1
        if ym_month > 12:
            ym_month = 1
            ym_year += 1
    return labels, months


@dashboard_bp.route('/dashboard')
@login_required
def index():
    current_app.logger.debug('Accediendo al dashboard...')
    user_email = getattr(current_user, 'email', None)
    if not user_email:
        return redirect(url_for('login.login_view'))

    # Build clients for each resource
    ideas_client = APIClient('idea')
    oportunidades_client = APIClient('oportunidad')
    soluciones_client = APIClient('solucion')

    # Fetch data from API
    try:
        ideas = ideas_client.get_ideas() or []
    except Exception as e:
        current_app.logger.exception('Error al obtener ideas')
        ideas = []

    try:
        oportunidades = oportunidades_client.get_oportunidades() or []
    except Exception as e:
        current_app.logger.exception('Error al obtener oportunidades')
        oportunidades = []

    try:
        soluciones = soluciones_client.get_soluciones() or []
    except Exception as e:
        current_app.logger.exception('Error al obtener soluciones')
        soluciones = []

    # Totals
    total_ideas = len(ideas)
    total_opportunities = len(oportunidades)
    total_projects = len(soluciones)

    # Recent activities: combine and sort by date
    recent_activities = []
    for idea in ideas:
        recent_activities.append({
            'type': 'idea',
            'title': idea.get('titulo') or idea.get('nombre') or 'Sin título',
            'date': idea.get('fecha_creacion')
        })
    for o in oportunidades:
        recent_activities.append({
            'type': 'oportunidad',
            'title': o.get('titulo') or o.get('nombre') or 'Sin título',
            'date': o.get('fecha_creacion')
        })
    for s in soluciones:
        recent_activities.append({
            'type': 'solucion',
            'title': s.get('titulo') or s.get('nombre') or 'Sin título',
            'date': s.get('fecha_creacion')
        })

    # Parse and sort recent activities by datetime descending
    for item in recent_activities:
        item['_parsed'] = parse_date(item.get('date'))
    recent_activities = [r for r in recent_activities if r.get('_parsed')]
    recent_activities.sort(key=lambda x: x['_parsed'], reverse=True)
    recent_activities = recent_activities[:10]

    # Determine latest date among all items (ideas, oportunidades, soluciones)
    def parse_item_date(it):
        # Try common date keys and formats; reuse parse_date for strings
        if not isinstance(it, dict):
            return None
        candidates = ['fecha_creacion', 'fechaCreacion', 'created_at', 'createdAt', 'created', 'fecha']
        for key in candidates:
            if key in it:
                v = it.get(key)
                if v is None:
                    continue
                if isinstance(v, datetime):
                    return v
                if isinstance(v, (int, float)):
                    try:
                        ts = int(v)
                        if ts > 10**12:
                            return datetime.fromtimestamp(ts / 1000.0)
                        return datetime.fromtimestamp(ts)
                    except Exception:
                        pass
                if isinstance(v, str):
                    s = v.strip()
                    if s.startswith('/Date(') and s.endswith(')/'):
                        try:
                            num = s[6:-2]
                            ts = int(num)
                            return datetime.fromtimestamp(ts / 1000.0)
                        except Exception:
                            pass
                    if s.isdigit():
                        try:
                            ts = int(s)
                            if ts > 10**12:
                                return datetime.fromtimestamp(ts / 1000.0)
                            return datetime.fromtimestamp(ts)
                        except Exception:
                            pass
                    dt = parse_date(s)
                    if dt:
                        return dt
        return None

    all_items = []
    all_items.extend(ideas)
    all_items.extend(oportunidades)
    all_items.extend(soluciones)
    latest = None
    for it in all_items:
        try:
            d = parse_item_date(it)
            if d and (latest is None or d > latest):
                latest = d
        except Exception:
            continue

    # If we found a latest date, end the window at that date; otherwise use now
    end_date = latest if latest is not None else datetime.now()

    # Prepare last 6 months labels and counts per resource ending at end_date
    def last_n_months_labels_end(n=6, end=end_date):
        # compute the earliest month (n-1 months ago relative to end)
        start_month = end.month - (n - 1)
        start_year = end.year
        while start_month <= 0:
            start_month += 12
            start_year -= 1
        labels = []
        months = []
        ym_year = start_year
        ym_month = start_month
        for _ in range(n):
            d = datetime(ym_year, ym_month, 1)
            labels.append(d.strftime('%b %Y'))
            months.append((ym_year, ym_month))
            ym_month += 1
            if ym_month > 12:
                ym_month = 1
                ym_year += 1
        return labels, months

    labels, months = last_n_months_labels_end(6, end_date)

    def monthly_counts(items):
            def get_item_date(it):
                # Try common date keys and formats
                candidates = ['fecha_creacion', 'fechaCreacion', 'created_at', 'createdAt', 'created', 'fecha']
                for key in candidates:
                    if isinstance(it, dict) and key in it:
                        v = it.get(key)
                        if v is None:
                            continue
                        # If already a datetime
                        if isinstance(v, datetime):
                            return v
                        # If numeric (epoch seconds or ms)
                        if isinstance(v, (int, float)):
                            # Heuristic: if > 10**12 assume milliseconds
                            try:
                                ts = int(v)
                                if ts > 10**12:
                                    return datetime.fromtimestamp(ts / 1000.0)
                                return datetime.fromtimestamp(ts)
                            except Exception:
                                pass
                        # If string, handle a few common variants
                        if isinstance(v, str):
                            s = v.strip()
                            # /Date(169...)\/ pattern (MS AJAX)
                            if s.startswith('/Date(') and s.endswith(')/'):
                                try:
                                    num = s[6:-2]
                                    ts = int(num)
                                    # usually milliseconds
                                    return datetime.fromtimestamp(ts / 1000.0)
                                except Exception:
                                    pass
                            # pure digits (epoch)
                            if s.isdigit():
                                try:
                                    ts = int(s)
                                    if ts > 10**12:
                                        return datetime.fromtimestamp(ts / 1000.0)
                                    return datetime.fromtimestamp(ts)
                                except Exception:
                                    pass
                            # fallback to parse_date which handles ISO and YYYY-MM-DD
                            dt = parse_date(s)
                            if dt:
                                return dt
                # as a last resort, try the original key if present
                if isinstance(it, dict) and 'fecha_creacion' in it:
                    return parse_date(it.get('fecha_creacion'))
                return None

            counts = [0] * len(months)
            for it in items:
                dt = get_item_date(it)
                if not dt:
                    continue
                for idx, (y, m) in enumerate(months):
                    if dt.year == y and dt.month == m:
                        counts[idx] += 1
                        break
            return counts

    data_ideas = monthly_counts(ideas)
    data_oportunidades = monthly_counts(oportunidades)
    data_soluciones = monthly_counts(soluciones)

    # Debug: log series so we can inspect formats when troubleshooting
    try:
        current_app.logger.debug('dashboard labels=%s', labels)
        current_app.logger.debug('data_ideas=%s', data_ideas)
        current_app.logger.debug('data_oportunidades=%s', data_oportunidades)
        current_app.logger.debug('data_soluciones=%s', data_soluciones)
    except Exception:
        pass

    user_data = {
        'email': user_email,
        'name': getattr(current_user, 'name', 'Usuario'),
        'role': getattr(current_user, 'role', 'Usuario')
    }

    # Calcular porcentajes respecto a las metas (opción A)
    meta_ideas = DASHBOARD_METAS.get('ideas', 100)
    meta_oportunidades = DASHBOARD_METAS.get('oportunidades', 50)
    meta_soluciones = DASHBOARD_METAS.get('soluciones', 75)

    def pct(total, meta):
        try:
            if not meta or meta <= 0:
                return 0
            value = int(round((total / float(meta)) * 100))
            if value < 0:
                value = 0
            if value > 100:
                value = 100
            return value
        except Exception:
            return 0

    pct_ideas = pct(total_ideas, meta_ideas)
    pct_oportunidades = pct(total_opportunities, meta_oportunidades)
    pct_soluciones = pct(total_projects, meta_soluciones)

    return render_template('dashboard.html',
                           user=user_data,
                           total_ideas=total_ideas,
                           total_opportunities=total_opportunities,
                           total_projects=total_projects,
                           recent_activities=recent_activities,
                           ideas_count=total_ideas,
                           oportunidades_count=total_opportunities,
                           solucion_count=total_projects,
                           now=datetime.now().strftime('%d/%m/%Y %H:%M:%S'),
                           activity_labels=labels,
                           data_ideas=data_ideas,
                           data_oportunidades=data_oportunidades,
                           data_soluciones=data_soluciones,
                           meta_ideas=meta_ideas,
                           meta_oportunidades=meta_oportunidades,
                           meta_soluciones=meta_soluciones,
                           pct_ideas=pct_ideas,
                           pct_oportunidades=pct_oportunidades,
                           pct_soluciones=pct_soluciones)


@dashboard_bp.route('/proyectos')
@login_required
def proyectos():
    # Lógica para cargar el dashboard
    return render_template('listar_proyectos.html')