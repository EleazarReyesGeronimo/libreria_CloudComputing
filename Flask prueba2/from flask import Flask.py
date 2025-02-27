from flask import Flask, jsonify
import mysql.connector

app = Flask(__name__)

# Configuración de la conexión a MySQL
db_config = {
    "host": "localhost",   # Cambia si tu MySQL está en otro servidor
    "user": "root",  # Reemplázalo con tu usuario de MySQL
    "password": "root",  # Reemplázalo con tu contraseña
    "database": "Libreria"
}

# Ruta para obtener los usuarios
@app.route('/Libro', methods=['GET'])
def get_libro():
    try:
        conn = mysql.connector.connect(**db_config)
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM Libro")
        usuarios = cursor.fetchall()
        cursor.close()
        conn.close()
        return jsonify(usuarios)  # Devuelve los datos en formato JSON
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True)