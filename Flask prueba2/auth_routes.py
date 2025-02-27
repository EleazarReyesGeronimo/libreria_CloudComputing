from flask import Blueprint, request, jsonify
import bcrypt
from dbprueba import get_db_connection

auth_bp = Blueprint('auth', __name__)

@auth_bp.route("/register", methods=["POST"])
def register():
    data = request.form
    usuario = data["new_username"]
    contrasena = data["new_password"].encode("utf-8")
    nombre = data["nombre"]
    apellido = data["apellido"]
    rol = data["rol"]

    hashed_password = bcrypt.hashpw(contrasena, bcrypt.gensalt())

    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO Personal_Manage (Usuario, Contrasena, Nombre, Apellido, Rol) 
            VALUES (%s, %s, %s, %s, %s)
        """, (usuario, hashed_password, nombre, apellido, rol))
        conn.commit()
        cursor.close()
        conn.close()
        return jsonify({"message": "Usuario registrado"}), 201
    except mysql.connector.IntegrityError:
        return jsonify({"error": "El usuario ya existe"}), 400

@auth_bp.route("/login", methods=["POST"])
def login():
    data = request.form
    usuario = data["username"]
    contrasena = data["password"].encode("utf-8")

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM Personal_Manage WHERE Usuario = %s", (usuario,))
    user = cursor.fetchone()
    cursor.close()
    conn.close()

    if user and bcrypt.checkpw(contrasena, user["Contrasena"].encode("utf-8")):
        return jsonify({"message": "Login exitoso", "Nombre": user["Nombre"], "Rol": user["Rol"]}), 200
    else:
        return jsonify({"error": "Credenciales incorrectas"}), 401
