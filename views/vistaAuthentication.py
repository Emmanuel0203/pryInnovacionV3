# views/auth.py
from flask import Blueprint, request, render_template, redirect, url_for, flash
from flask_login import login_user
from utils.api_client import APIClient
from werkzeug.security import check_password_hash
from models.Usuario import Usuario

auth_bp = Blueprint("auth", __name__)

@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form["email"]
        password = request.form["password"]

        client = APIClient("usuario")
        result = client.get_data(where_condition=f"email = '{email}'")

        if result:
            user_data = result[0]  # suponemos un solo usuario
            if check_password_hash(user_data["password"], password):
                user = Usuario(user_data)
                login_user(user)
                flash("Inicio de sesión exitoso", "success")
                return redirect(url_for("home.index"))
            else:
                flash("Contraseña incorrecta", "danger")
        else:
            flash("Usuario no encontrado", "danger")

    return render_template("auth/login.html")
