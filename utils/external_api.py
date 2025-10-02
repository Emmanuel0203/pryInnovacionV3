import requests

class FocoInnovacionAPI:
    BASE_URL = "http://190.217.58.246:5186/api/sgv/foco_innovacion"

    @staticmethod
    def get_focos():
        try:
            response = requests.get(FocoInnovacionAPI.BASE_URL)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"[FocoInnovacionAPI] Error: {e}")
            return []


class TipoInnovacionAPI:
    BASE_URL = "http://190.217.58.246:5186/api/sgv/tipo_innovacion"

    @staticmethod
    def get_tipos():
        try:
            response = requests.get(TipoInnovacionAPI.BASE_URL)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"[TipoInnovacionAPI] Error: {e}")
            return []
