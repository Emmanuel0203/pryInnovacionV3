"""api_client.py

Restored/extended APIClient with support for:
- session-wide headers (api key / authorization)
- authenticate(...) helper to obtain a JWT token from the backend
- set_api_key(...) to dynamically set/remove API key header

This file intentionally keeps relaxed SSL verification for local dev; remove or
change `self.session.verify` for production environments.
"""
import requests
import os
import urllib3
from typing import Optional

# Deshabilitar advertencias de SSL para desarrollo local (no para producción)
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


class APIClient:
    """Cliente genérico para interactuar con la API local.

    base_url is expected to include the /api portion if your backend uses it
    (for example: http://localhost:5186/api).
    """

    def __init__(self, table_name: str, schema: str = "public"):
        self.table_name = table_name
        self.schema = schema
        self.base_url = os.getenv("BACKEND_LOCAL_URL")

        # Crear sesión para reusar conexiones y encabezados
        self.session = requests.Session()
        # Verificación SSL deshabilitada por comodidad en desarrollo
        self.session.verify = False

        # Si hay una API key configurada en env, usarla como header por defecto
        api_key = os.getenv("BACKEND_API_KEY")
        if api_key:
            self.session.headers.update({"x-api-key": api_key})

        # Debug mínima
        # Use current_app.logger in runtime; print useful when running scripts
        print(f"[DEBUG APIClient] Tabla: {table_name}, Base URL: {self.base_url}")

    def _make_request(self, method: str = "GET", endpoint: str = "", payload: Optional[dict] = None, files=None, **params):
        # Build URL
        if not self.base_url:
            raise RuntimeError("BACKEND_LOCAL_URL no está configurada en el entorno")

        url = f"{self.base_url}/{endpoint}" if endpoint else f"{self.base_url}/{self.table_name}"
        headers = {"Content-Type": "application/json"} if not files else None

        # Preferir session.request para conservar headers (Authorization, API-Key)
        # Optional debug: print outgoing headers when BACKEND_DEBUG_API_HEADERS=1
        try:
            if os.getenv('BACKEND_DEBUG_API_HEADERS') == '1':
                try:
                    # If running inside a Flask request, show masked session token and session keys
                    try:
                        from flask import has_request_context, session as flask_session
                        if has_request_context():
                            token = flask_session.get('api_token')
                            try:
                                masked = (str(token)[:8] + '...') if token and len(str(token)) > 12 else token
                            except Exception:
                                masked = '<unavailable>'
                            print(f"[DEBUG SESSION TOKEN] masked={masked}")
                            try:
                                print(f"[DEBUG SESSION KEYS] {list(flask_session.keys())}")
                            except Exception:
                                pass
                    except Exception:
                        # Not running under Flask or session unavailable
                        pass

                    print(f"[DEBUG OUTGOING HEADERS] {self.session.headers}")
                except Exception:
                    pass
        except Exception:
            pass
        try:
            if method.upper() == "GET":
                r = self.session.get(url, params=params, timeout=10)
            elif method.upper() == "POST":
                if files:
                    r = self.session.post(url, data=payload, files=files, timeout=15)
                else:
                    r = self.session.post(url, json=payload, params=params, timeout=10)
            elif method.upper() == "PUT":
                r = self.session.put(url, json=payload, params=params, timeout=10)
            elif method.upper() == "DELETE":
                r = self.session.delete(url, params=params, timeout=10)
            else:
                raise ValueError(f"Método HTTP no soportado: {method}")

            r.raise_for_status()

            # Return parsed JSON where possible
            try:
                return r.json()
            except ValueError:
                return r.text

        except requests.exceptions.RequestException as exc:
            # Surface debug info when available
            print(f"[ERROR] Error en {method} {url}: {exc}")
            if hasattr(exc, 'response') and exc.response is not None:
                try:
                    print(f"[ERROR] Response ({getattr(exc.response,'status_code',None)}): {exc.response.text}")
                except Exception:
                    pass
            return None

    def _wrap_payload(self, data_list):
        return data_list if isinstance(data_list, list) else [data_list]

    # --- convenience wrappers ---
    def get_data(self, **kwargs):
        resp = self._make_request("GET", self.table_name, **kwargs)
        return resp.get("datos", []) if isinstance(resp, dict) and resp else (resp or [])

    def insert_data(self, json_data):
        return self._make_request("POST", self.table_name, payload=json_data)

    def update_data(self, record_id, json_data):
        endpoint = f"{self.table_name}/{record_id}"
        return self._make_request("PUT", endpoint, payload=json_data)

    def delete_data(self, record_id):
        endpoint = f"{self.table_name}/{record_id}"
        return self._make_request("DELETE", endpoint)

    def fetch_endpoint_data(self, endpoint):
        resp = self._make_request("GET", endpoint)
        if isinstance(resp, dict) and "datos" in resp:
            return resp["datos"]
        if isinstance(resp, list):
            return resp
        return []

    def get_all(self, resource=None):
        endpoint = f"{self.table_name}/{resource}" if resource else self.table_name
        resp = self._make_request("GET", endpoint)
        if isinstance(resp, dict) and "datos" in resp:
            return resp["datos"]
        if isinstance(resp, list):
            return resp
        return []

    def get_by_id(self, id_field, record_id):
        endpoint = f"{self.table_name}?{id_field}={record_id}"
        resp = self._make_request("GET", endpoint)
        return resp.get("datos", []) if isinstance(resp, dict) and resp else None

    def update_by_key(self, key_name, key_value, json_data, schema=None, campos_encriptar=None):
        endpoint = f"{self.table_name}/{key_name}/{key_value}"
        params = {}
        if schema:
            params["esquema"] = schema
        if campos_encriptar:
            params["camposEncriptar"] = campos_encriptar
        return self._make_request("PUT", endpoint, payload=json_data, **params)

    def get_by_key(self, key_name, key_value):
        endpoint = f"{self.table_name}/{key_name}/{key_value}"
        resp = self._make_request("GET", endpoint)
        return resp.get("datos", []) if isinstance(resp, dict) and resp else None

    def delete_by_key(self, key_name, key_value, schema=None):
        endpoint = f"{self.table_name}/{key_name}/{key_value}"
        params = {}
        if schema:
            params["esquema"] = schema
        return self._make_request("DELETE", endpoint, **params)

    # --- auth / api key helpers ---
    def set_api_key(self, api_key: Optional[str], header_name: str = "x-api-key"):
        """Set or remove an API key header on the session."""
        if api_key:
            self.session.headers.update({header_name: api_key})
        else:
            if header_name in self.session.headers:
                del self.session.headers[header_name]

    def authenticate(self, usuario: str, contrasena: str, tabla: str = "usuario", campoUsuario: str = "email", campoContrasena: str = "password", use_hash: bool = False) -> Optional[dict]:
        """Authenticate against the backend, set Authorization header on success and
        return a dictionary with token and expiracion.

        Returns a dict like {"token": <str>, "expiracion": <str|datetime>, "raw": <response dict>} or None on failure.
        """
        if not self.base_url:
            raise RuntimeError("BACKEND_LOCAL_URL no está configurada en el entorno")

        payload = {
            "tabla": tabla,
            "campoUsuario": campoUsuario,
            "campoContrasena": campoContrasena,
            "usuario": usuario,
            "contrasena": contrasena
        }

        # Ensure we call the Autenticacion endpoint under /api. If BACKEND_LOCAL_URL already
        # includes '/api' we'll avoid duplicating it.
        base = self.base_url.rstrip('/')
        if base.endswith('/api') or '/api/' in base:
            url = f"{base}/Autenticacion/token"
        else:
            url = f"{base}/api/Autenticacion/token"

        try:
            r = self.session.post(url, json=payload, timeout=10)
            r.raise_for_status()
            data = r.json()

            # Extract token and expiration from common fields
            token = None
            expiracion = None
            if isinstance(data, dict):
                token = data.get("token") or data.get("access_token") or data.get("apiKey") or data.get("api_key")
                expiracion = data.get("expiracion") or data.get("expiration") or data.get("exp") or data.get("expires")

            if token:
                # Store Authorization header for future requests
                self.session.headers.update({"Authorization": f"Bearer {token}"})
                return {"token": token, "expiracion": expiracion, "raw": data}

            # No token in response
            print(f"[AUTH WARN] No token in response from {url}: {data}")
            return None

        except requests.exceptions.RequestException as exc:
            
            print(f"[AUTH ERROR] Error obtaining token: {exc}")
            try:
                if hasattr(exc, 'response') and exc.response is not None:
                    print(f"[AUTH ERROR] Response: {exc.response.status_code} {exc.response.text}")
            except Exception:
                pass
            return None


def get_api_client(table_name: str) -> APIClient:
    """Factory helper: create an APIClient and restore Authorization header from
    Flask session when a request context exists.

    Safe to call outside a request context: it will simply return a plain APIClient.
    """
    try:
        # Import locally to avoid requiring Flask when this module is used in scripts
        from flask import has_request_context, session
        client = APIClient(table_name)
        if has_request_context():
            token = session.get('api_token')
            if token:
                client.session.headers.update({'Authorization': f'Bearer {token}'})
        return client
    except Exception:
        # If Flask is not available or session access fails, return plain client
        return APIClient(table_name)

