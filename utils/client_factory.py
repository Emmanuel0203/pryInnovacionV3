from flask import session, has_request_context
from utils.api_client import APIClient


def get_api_client(table_name: str) -> APIClient:
    """Return an APIClient with Authorization header restored from Flask session if present.

    Safe to call outside of a request context: when there's no active request the
    function returns a plain APIClient without Authorization header.
    """
    client = APIClient(table_name)
    try:
        if has_request_context():
            token = session.get('api_token')
            if token:
                client.session.headers.update({'Authorization': f'Bearer {token}'})
    except RuntimeError:
        # In case session access still fails for unexpected reasons, silently continue
        pass
    return client
