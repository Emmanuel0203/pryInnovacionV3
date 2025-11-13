from functools import wraps
from flask import session, flash, redirect, url_for, current_app
from typing import List
from .api_client import get_api_client


def _extract_role_names(user_obj) -> List[str]:
    """Try to extract a list of role names from a user dict returned by the API."""
    if not user_obj or not isinstance(user_obj, dict):
        return []

    # Common shapes: 'roles': [ { 'nombre': 'Administrador' } ], or 'rol_nombre', or 'rol'
    roles = []
    if 'roles' in user_obj and isinstance(user_obj['roles'], list):
        for r in user_obj['roles']:
            if isinstance(r, dict):
                name = r.get('nombre') or r.get('descripcion') or r.get('rol_nombre') or r.get('name')
                if name:
                    roles.append(str(name))
            elif isinstance(r, str):
                roles.append(r)

    # Single role fields (common shapes). Explicitly handle 'rol' and nested 'perfil'.
    if 'rol' in user_obj and isinstance(user_obj.get('rol'), str):
        roles.append(user_obj.get('rol'))

    for key in ('rol_nombre', 'nombre_rol', 'role', 'roles_nombre'):
        if key in user_obj:
            val = user_obj.get(key)
            if isinstance(val, str):
                roles.append(val)
            elif isinstance(val, dict):
                name = val.get('nombre') or val.get('descripcion') or val.get('name')
                if name:
                    roles.append(name)

    # Perfil can be a nested dict with role information or a FK id; we'll handle nested dicts here.
    if 'perfil' in user_obj:
        perfil_val = user_obj.get('perfil')
        if isinstance(perfil_val, str):
            roles.append(perfil_val)
        elif isinstance(perfil_val, dict):
            # Some APIs put the role name under 'rol', 'nombre' or 'descripcion' inside perfil
            name = perfil_val.get('rol') or perfil_val.get('nombre') or perfil_val.get('descripcion') or perfil_val.get('role')
            if name:
                roles.append(name)

    # Some APIs return direct FK fields; try to map fkidrol -> human name is not available here
    # In that case, return empty and rely on other mechanisms.

    # Normalize and dedupe
    cleaned = []
    for r in roles:
        if not isinstance(r, str):
            continue
        rr = r.strip()
        if rr and rr not in cleaned:
            cleaned.append(rr)
    return cleaned


def ensure_user_roles_loaded():
    """Ensure session['user_roles'] is populated. Attempts to fetch current user from API if needed."""
    if session.get('user_roles'):
        return session['user_roles']

    user_email = session.get('user_email')
    if not user_email:
        return []
    try:
        # First, try to locate the perfil record that references this usuario by email.
        perfil_client = get_api_client('perfil')
        try:
            perfil_resp = perfil_client.get_by_key('usuario_email', user_email)
        except Exception:
            perfil_resp = None

        perfil_obj = None
        if isinstance(perfil_resp, list) and perfil_resp:
            perfil_obj = perfil_resp[0]
        elif isinstance(perfil_resp, dict):
            perfil_obj = perfil_resp.get('datos') or perfil_resp

        if perfil_obj and isinstance(perfil_obj, dict):
            # Extract role from perfil (common field: 'rol')
            p_name = perfil_obj.get('rol') or perfil_obj.get('role') or perfil_obj.get('nombre') or perfil_obj.get('descripcion')
            roles = []
            if p_name:
                roles.append(p_name)
                session['user_roles'] = roles
                session['is_admin'] = any(r.lower() == 'administrador' for r in roles)
                return roles

        # Fallback: try to get the user record and extract roles or resolve perfil FK from there
        client = get_api_client('usuario')
        # Try query by email using ?email=... style
        data = client.get_by_id('email', user_email)
        # client.get_by_id returns list or object; normalize
        if isinstance(data, list) and data:
            user_obj = data[0]
        elif isinstance(data, dict):
            # Some APIs return { 'datos': {...} } or single object
            # If it's a wrapper with 'datos' key, try to unwrap
            if 'datos' in data and isinstance(data['datos'], list) and data['datos']:
                user_obj = data['datos'][0]
            else:
                user_obj = data
        else:
            user_obj = None

        # If the role is stored in a separate perfil record (FK), try to resolve it.
        roles = _extract_role_names(user_obj)
        if not roles and user_obj and isinstance(user_obj, dict):
            # Look for common FK fields that reference perfil
            for fk_key in ('fkidperfil', 'perfil_id', 'id_perfil', 'perfilId', 'perfil'):
                if fk_key in user_obj and not isinstance(user_obj.get(fk_key), dict):
                    perfil_id = user_obj.get(fk_key)
                    try:
                        perfil_client = get_api_client('perfil')
                        perfil_data = None
                        # Try a couple of request patterns
                        perfil_resp2 = perfil_client.get_by_id('id', perfil_id)
                        if isinstance(perfil_resp2, list) and perfil_resp2:
                            perfil_data = perfil_resp2[0]
                        elif isinstance(perfil_resp2, dict):
                            perfil_data = perfil_resp2.get('datos') or perfil_resp2
                        if perfil_data and isinstance(perfil_data, dict):
                            # extract role name from perfil
                            p_name = perfil_data.get('rol') or perfil_data.get('nombre') or perfil_data.get('descripcion')
                            if p_name:
                                roles.append(p_name)
                                break
                    except Exception:
                        current_app.logger.exception('Error al obtener perfil por FK %s', fk_key)
                        continue
        # Persist roles if found
        if roles:
            session['user_roles'] = roles
            session['is_admin'] = any(r.lower() == 'administrador' for r in roles)
            return roles
    except Exception as exc:
        current_app.logger.exception('No se pudo cargar roles del usuario: %s', exc)
        session['user_roles'] = []
        session['is_admin'] = False
        return []

    # Default empty
    session['user_roles'] = []
    session['is_admin'] = False
    return []


def deny_roles(forbidden: List[str]):
    """Decorator to deny access to users having any of the forbidden role names.

    Admins (role name 'Administrador') bypass the check and are always allowed.
    """
    forbidden_normalized = [f.lower() for f in (forbidden or [])]

    def decorator(f):
        @wraps(f)
        def wrapped(*args, **kwargs):
            # Ensure roles are loaded
            roles = ensure_user_roles_loaded()

            # Admin bypass
            if session.get('is_admin') or any(r.lower() == 'administrador' for r in (roles or [])):
                return f(*args, **kwargs)

            # If any role in user's roles is forbidden, block
            for r in roles or []:
                if r.lower() in forbidden_normalized:
                    flash('No tienes permisos para acceder a esta sección.', 'warning')
                    return redirect(url_for('main.menu'))

            # Otherwise allow
            return f(*args, **kwargs)

        return wrapped

    return decorator
