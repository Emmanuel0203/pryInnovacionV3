# api_client.py - ADAPTADO A TU NUEVA API
import requests
import os

class APIClient:
    """Cliente genérico para interactuar con la API local de Innovación."""

    def __init__(self, table_name: str, schema: str = "por defecto"):
        self.table_name = table_name
        self.schema = schema
        self.base_url = os.getenv("BACKEND_LOCAL_URL")  # ej: http://localhost:5186/api/
        # print(f"[DEBUG] URL base configurada: {self.base_url}")

    def _make_request(self, method="GET", endpoint="", payload=None, files=None, **params):
        url = f"{self.base_url}/{endpoint}" if endpoint else f"{self.base_url}/{self.table_name}"
        headers = {"Content-Type": "application/json"} if not files else None
        # print(f"[DEBUG] Enviando solicitud {method} a {url} con headers: {headers}")

        try:
            if method.upper() == "GET":
                response = requests.get(url, params=params, headers=headers, timeout=10)
            elif method.upper() == "POST":
                if files:
                    response = requests.post(url, data=payload, files=files, timeout=15)
                else:
                    response = requests.post(url, json=payload, headers=headers, timeout=10)
            elif method.upper() == "PUT":
                response = requests.put(url, json=payload, headers=headers, timeout=10)
            elif method.upper() == "DELETE":
                response = requests.delete(url, headers=headers, timeout=10)
            else:
                raise ValueError(f"Método HTTP no soportado: {method}")

            response.raise_for_status()
            print(f"[DEBUG] Respuesta recibida: {response.status_code}")
            return response.json()

        except requests.exceptions.RequestException as e:
            print(f"[ERROR] Error en {method} {url}: {e}")
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
        list
            Un arreglo de diccionarios con los datos a insertar/actualizar.
        """
        return data_list if isinstance(data_list, list) else [data_list]

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
        # Enviar el payload directamente como un objeto JSON
        print(f"[DEBUG] Payload enviado: {json_data}")
        response = self._make_request("POST", self.table_name, payload=json_data)
        if response:
            print(f"[DEBUG] Respuesta de la API: {response}")
        else:
            print("[ERROR] No se recibió respuesta de la API")
        return response

    def update_data(self, record_id, json_data):
        """Actualiza datos de un registro específico."""
        payload = self._wrap_payload(json_data)
        endpoint = f"{self.table_name}/{record_id}"
        print(f"[DEBUG] Payload enviado para actualización: {payload}")
        return self._make_request("PUT", endpoint, payload=payload)

    def delete_data(self, record_id):
        """Elimina un registro específico."""
        endpoint = f"{self.table_name}/{record_id}"
        print(f"[DEBUG] Eliminando registro con ID: {record_id}")
        return self._make_request("DELETE", endpoint)

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
            return response.json().get("datos", [])
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
            return response.get("datos", []) if response else []
        except Exception as e:
            print(f"Error fetching records: {e}")
            return []

    def get_by_id(self, id_field, record_id):
        """
        Fetch a specific record by its ID.

        Parameters
        ----------
        id_field : str
            The name of the ID field (e.g., 'codigo_solucion').
        record_id : int
            The ID of the record to fetch.

        Returns
        -------
        dict or None
            The record if found, otherwise None.
        """
        endpoint = f"{self.table_name}?{id_field}={record_id}"
        response = self._make_request("GET", endpoint)
        return response.get("datos", []) if response else None

    def confirm(self, id_field, record_id):
        """
        Confirms a specific record by its ID.

        Parameters
        ----------
        id_field : str
            The name of the ID field (e.g., 'codigo_solucion').
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
        """
        Fetches all ideas from the API.

        Returns
        -------
        list
            A list of ideas fetched from the API, or an empty list if an error occurs.
        """
        return self.fetch_endpoint_data("idea")

    def get_oportunidades(self):
        """
        Fetches all opportunities from the API.

        Returns
        -------
        list
            A list of opportunities fetched from the API, or an empty list if an error occurs.
        """
        return self.fetch_endpoint_data("oportunidad")

    def get_soluciones(self):
        """
        Fetches all solutions from the API.

        Returns
        -------
        list
            A list of solutions fetched from the API, or an empty list if an error occurs.
        """
        return self.fetch_endpoint_data("solucion")

    def update_by_key(self, key_name, key_value, json_data, schema=None, campos_encriptar=None):
        """
        Actualiza un registro específico en la tabla usando el método ActualizarAsync.

        Parameters
        ----------
        key_name : str
            El nombre del campo clave (e.g., 'codigo_solucion').
        key_value : str | int
            El valor del campo clave (e.g., 13).
        json_data : dict
            Los datos a actualizar en formato JSON.
        schema : str, optional
            Esquema de la base de datos (e.g., 'public').
        campos_encriptar : str, optional
            Campos a encriptar (e.g., 'password,pin').

        Returns
        -------
        dict or None
            La respuesta de la API si es exitosa, de lo contrario None.
        """
        endpoint = f"{self.table_name}/{key_name}/{key_value}"
        params = {}
        if schema:
            params["esquema"] = schema
        if campos_encriptar:
            params["camposEncriptar"] = campos_encriptar

        return self._make_request("PUT", endpoint, payload=json_data, **params)

    def get_by_key(self, key_name, key_value):
        """
        Obtiene un registro específico usando el método ObtenerPorClaveAsync.

        Parameters
        ----------
        key_name : str
            El nombre del campo clave (e.g., 'codigo_solucion').
        key_value : str | int
            El valor del campo clave (e.g., 13).

        Returns
        -------
        dict or None
            El registro si se encuentra, de lo contrario None.
        """
        endpoint = f"{self.table_name}/{key_name}/{key_value}"
        response = self._make_request("GET", endpoint)
        return response.get("datos", []) if response else None

    def delete_by_key(self, key_name, key_value, schema=None):
        """
        Elimina un registro específico usando el método EliminarAsync.

        Parameters
        ----------
        key_name : str
            El nombre del campo clave (e.g., 'codigo_solucion').
        key_value : str | int
            El valor del campo clave (e.g., 13).
        schema : str, optional
            Esquema de la base de datos (e.g., 'public').

        Returns
        -------
        dict or None
            La respuesta de la API si es exitosa, de lo contrario None.
        """
        endpoint = f"{self.table_name}/{key_name}/{key_value}"
        params = {}
        if schema:
            params["esquema"] = schema

        return self._make_request("DELETE", endpoint, **params)
