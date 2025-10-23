from utils.api_client import APIClient
import logging
import json

proc_client = APIClient("procedimientos")
logger = logging.getLogger(__name__)


def crear_usuario_con_roles(email: str, password: str, roles_list: list,
                            campos_encriptar: str = "p_password",
                            is_active: bool = True,
                            is_staff: bool = False,
                            is_superuser: bool = False) -> dict:
    """
    Helper que encapsula la llamada al endpoint de procedimientos para crear usuario con roles.

    - email: str
    - password: str
    - roles_list: list of dicts: [{"fkidrol":1, "fkidaplicacion":2}, ...]
    - campos_encriptar: nombre del parámetro que debe ser hasheado en servidor (default p_password)

    Retorna el JSON de respuesta o lanza RuntimeError en error de comunicación.
    """
    endpoint = f"procedimientos/ejecutarsp?camposEncriptar={campos_encriptar}"
    payload = {
        "nombreSP": "crear_usuario_con_roles",
        "p_email": email,
        "p_password": password,
        "p_roles": roles_list,
        "p_is_active": is_active,
        "p_is_staff": is_staff,
        "p_is_superuser": is_superuser
    }

    resp = proc_client._make_request("POST", endpoint, payload=payload)
    if not resp:
        logger.error("No se obtuvo respuesta del backend al ejecutar crear_usuario_con_roles")
        raise RuntimeError("No se obtuvo respuesta del backend al ejecutar crear_usuario_con_roles")
    return resp
