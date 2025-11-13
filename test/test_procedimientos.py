"""
Simple test script to exercise utils.procedimientos.crear_usuario_con_roles.
Run this from the project root where the Flask app can access the same env (or from your venv):

python -m test.test_procedimientos

It will attempt to create a user with a unique timestamped email. The script prints the response JSON or the error.
"""
import time
import pprint

from utils.procedimientos import crear_usuario_con_roles


def make_test_user():
    ts = int(time.time())
    email = f"test_user_{ts}@example.com"
    password = "TestPass123!"
    roles = [
        {"fkidrol": 2, "fkidaplicacion": 1}
    ]
    try:
        resp = crear_usuario_con_roles(email, password, roles)
        pprint.pprint(resp)
    except Exception as e:
        print("Error calling crear_usuario_con_roles:", e)


if __name__ == "__main__":
    make_test_user()
