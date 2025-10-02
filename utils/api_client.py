# api_client.py - ADAPTADO A TU NUEVA API
import requests
import os

class APIClient:
    """Cliente genérico para interactuar con la API local de Innovación."""

    def __init__(self, table_name: str, schema: str = "por defecto"):
        self.table_name = table_name
        self.schema = schema
        self.base_url = os.getenv("BACKEND_LOCAL_URL")  # ej: http://localhost:5186/api/sgv

    def _make_request(self, method="GET", endpoint="", payload=None, **params):
        """Hace una petición a la API con el formato esperado."""
        url = f"{self.base_url}/{endpoint}" if endpoint else f"{self.base_url}/{self.table_name}"

        try:
            if method.upper() == "GET":
                response = requests.get(url, params=params, timeout=10)
            elif method.upper() in ["POST", "PUT", "DELETE"]:
                response = requests.request(method, url, json=payload, timeout=10)
            else:
                raise ValueError(f"Método HTTP no soportado: {method}")

            response.raise_for_status()
            return response.json()

        except requests.exceptions.RequestException as e:
            print(f"[APIClient] Error en {method} {url}: {e}")
            return None

    def _wrap_payload(self, data_list):
        """
        Construye el JSON con el formato esperado por la API.

        Parameters
        ----------
        data_list : dict | list[dict]
            Los registros a insertar/actualizar. Puede ser un único diccionario 
            (un solo registro) o una lista de diccionarios (varios registros).

        Returns
        -------
        dict
            Un JSON en el formato requerido por la API, con la estructura:
            {
                "tabla": "<nombre de la tabla>",
                "esquema": "<nombre del esquema>",
                "datos": [ {...}, {...}, ... ]
            }
        """
        return {
            "tabla": self.table_name,
            "esquema": self.schema,
            "datos": data_list if isinstance(data_list, list) else [data_list]
        }


    def get_data(self, **kwargs):
        """Obtiene datos de la tabla."""
        resp = self._make_request("GET", self.table_name, **kwargs)
        return resp.get("datos", []) if resp else []

    def get_user_by_email(self, email):
        """Busca un usuario por email."""
        users = self.get_data()
        for user in users:
            if user.get("email") == email:
                return user
        return None

    def insert_data(self, json_data):
        """Inserta datos en la tabla (requiere lista o dict)."""
        payload = self._wrap_payload(json_data)
        return self._make_request("POST", self.table_name, payload=payload)

    def update_data(self, record_id, json_data):
        """Actualiza datos de un registro específico."""
        payload = self._wrap_payload(json_data)
        endpoint = f"{self.table_name}/{record_id}"
        return self._make_request("PUT", endpoint, payload=payload)

    def delete_data(self, record_id):
        """Elimina un registro específico."""
        payload = self._wrap_payload({"id": record_id})
        endpoint = f"{self.table_name}/{record_id}"
        return self._make_request("DELETE", endpoint, payload=payload)
