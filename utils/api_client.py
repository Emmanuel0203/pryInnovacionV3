# api_client.py - CORREGIDO
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
        Construye el JSON con el formato esperado por ALGUNOS endpoints de la API.
        NOTA: No todos los endpoints requieren este formato.
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
        """
        Inserta datos en la tabla.
        Envía el objeto directamente sin envolver (formato esperado por .NET).
        
        Parameters
        ----------
        json_data : dict
            Diccionario con los datos del nuevo registro.
            
        Returns
        -------
        dict or None
            Respuesta de la API o None si hay error.
        """
        # ✅ CORREGIDO: Enviar datos directamente, sin _wrap_payload
        return self._make_request("POST", self.table_name, payload=json_data)

    def insert_data_bulk(self, json_data_list):
        """
        Inserta múltiples registros (si la API soporta bulk insert).
        Usa el formato envuelto con tabla/esquema/datos.
        
        Parameters
        ----------
        json_data_list : list[dict]
            Lista de diccionarios con los datos a insertar.
            
        Returns
        -------
        dict or None
            Respuesta de la API o None si hay error.
        """
        payload = self._wrap_payload(json_data_list)
        return self._make_request("POST", self.table_name, payload=payload)

    def update_data(self, record_id, json_data):
        """Actualiza datos de un registro específico."""
        # Si tu API .NET requiere el objeto directo, usa:
        endpoint = f"{self.table_name}/{record_id}"
        return self._make_request("PUT", endpoint, payload=json_data)
        
        # Si requiere formato envuelto, usa:
        # payload = self._wrap_payload(json_data)
        # return self._make_request("PUT", endpoint, payload=payload)

    def update(self, id_field, record_id, json_data):
        """
        Alias mejorado para update_data que acepta el campo ID explícitamente.
        """
        return self.update_data(record_id, json_data)

    def delete_data(self, record_id):
        """Elimina un registro específico."""
        endpoint = f"{self.table_name}/{record_id}"
        return self._make_request("DELETE", endpoint)

    def delete(self, id_field, record_id):
        """Alias para delete_data que acepta el campo ID explícitamente."""
        return self.delete_data(record_id)

    def fetch_endpoint_data(self, endpoint):
        """
        Fetches data from a specific API endpoint.

        Parameters
        ----------
        endpoint : str
            The endpoint to fetch data from (e.g., 'foco_innovacion').

        Returns
        -------
        list
            A list of data fetched from the API, or an empty list if an error occurs.
        """
        try:
            response = requests.get(f"{self.base_url}/{endpoint}", timeout=10)
            response.raise_for_status()
            data = response.json()
            # Manejar tanto respuestas con "datos" como respuestas directas
            if isinstance(data, dict) and "datos" in data:
                return data["datos"]
            elif isinstance(data, list):
                return data
            return []
        except requests.exceptions.RequestException as e:
            print(f"[APIClient] Error fetching data from endpoint '{endpoint}': {e}")
            return []

    def get_all(self, resource=None):
        """
        Fetch all records or filter by a specific resource.

        Parameters
        ----------
        resource : str, optional
            The resource to filter by (e.g., 'foco_innovacion').

        Returns
        -------
        list
            A list of data fetched from the API, or an empty list if an error occurs.
        """
        try:
            endpoint = f"{self.table_name}/{resource}" if resource else self.table_name
            response = self._make_request("GET", endpoint)
            if response and "datos" in response:
                return response["datos"]
            elif isinstance(response, list):
                return response
            return []
        except Exception as e:
            print(f"Error fetching records: {e}")
            return []

    def get_by_id(self, id_field, record_id):
        """
        Fetch a specific record by its ID.

        Parameters
        ----------
        id_field : str
            The name of the ID field (e.g., 'codigo_idea').
        record_id : int
            The ID of the record to fetch.

        Returns
        -------
        list or None
            Lista con el registro si se encuentra, o None si hay error.
        """
        endpoint = f"{self.table_name}?{id_field}={record_id}"
        response = self._make_request("GET", endpoint)
        if response and "datos" in response:
            return response["datos"]
        return None

    def confirm(self, id_field, record_id):
        """
        Confirms a specific record by its ID.

        Parameters
        ----------
        id_field : str
            The name of the ID field (e.g., 'codigo_idea').
        record_id : int
            The ID of the record to confirm.

        Returns
        -------
        dict or None
            The response from the API if successful, otherwise None.
        """
        endpoint = f"{self.table_name}/confirm"
        payload = {id_field: record_id}
        return self._make_request("POST", endpoint, payload=payload)

    def get_ideas(self):
        """Fetches all ideas from the API."""
        return self.fetch_endpoint_data("idea")

    def get_oportunidades(self):
        """Fetches all opportunities from the API."""
        return self.fetch_endpoint_data("oportunidad")

    def get_soluciones(self):
        """Fetches all solutions from the API."""
        return self.fetch_endpoint_data("solucion")