from flask import Flask, render_template, request, redirect, url_for, flash, session
import mysql.connector

app = Flask(__name__)
app.secret_key = 'supersecretkey'  # Necesario para manejar sesiones y mensajes flash

# Configuración de la base de datos
db_config = {
    'host': 'localhost',
    'user': 'root',  # Cambia esto por tu usuario de MySQL
    'password': 'root',  # Cambia esto por tu contraseña de MySQL
    'database': 'Libreria'
}

def get_db_connection():
    conn = mysql.connector.connect(**db_config)
    return conn

@app.route('/')
def home():
    return render_template('Login.html')

@app.route('/login', methods=['POST'])
def login():
    username = request.form['Usuario']
    password = request.form['Contrasena']

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    # Consulta para verificar las credenciales del usuario
    query = "SELECT * FROM Personal_Manage WHERE Usuario = %s AND Contrasena = %s"
    cursor.execute(query, (username, password))
    user = cursor.fetchone()

    cursor.close()
    conn.close()

    if user:
        session['user_id'] = user['IDpersonal']
        session['username'] = user['Usuario']
        session['role'] = user['Rol']
        flash('Login exitoso!', 'success')
        return redirect(url_for('dashboard'))
    else:
        flash('Usuario o contraseña incorrectos', 'error')
        return redirect(url_for('home'))

@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        flash('Por favor, inicia sesión primero', 'error')
        return redirect(url_for('home'))

    return render_template('dashboard.html', username=session['username'], role=session['role'])

@app.route('/logout')
def logout():
    session.clear()
    flash('Has cerrado sesión correctamente', 'success')
    return redirect(url_for('home'))

if __name__ == '__main__':
    app.run(debug=True)
