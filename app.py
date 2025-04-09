from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
from flask_mail import Mail, Message
import mysql.connector
from datetime import datetime, timedelta
from werkzeug.utils import secure_filename
import os
import requests
from functools import wraps
from datetime import datetime, timedelta
from datetime import datetime
import uuid
import hashlib
from fpdf import FPDF
import yaml
from functools import lru_cache
from flask_wtf import FlaskForm
from wtforms import StringField, BooleanField, SubmitField
from wtforms.validators import DataRequired, URL



app = Flask(__name__)
app.secret_key = 'your_secret_key'  # Necesario para usar sesiones

class MenuForm(FlaskForm):
    name = StringField('Nombre', validators=[DataRequired()])
    url = StringField('URL', validators=[DataRequired(), URL()])
    icon = StringField('Icono (clase Bootstrap Icons)')
    visible = BooleanField('Visible')
    admin_only = BooleanField('Solo Admin')
    submit = SubmitField('Guardar')

# Configuración de Flask-Mail (asegúrate que esté correcta)
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = 'libreriautez@gmail.com'
app.config['MAIL_PASSWORD'] = 'orud zsfq lktx ddvl'  # Usa la contraseña de aplicación correcta
app.config['MAIL_DEFAULT_SENDER'] = 'libreriautez@gmail.com'

mail = Mail(app)

# Configura la carpeta donde se guardarán las imágenes
UPLOAD_FOLDER = 'static/images'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# IP pública de prueba (puedes cambiarla para probar diferentes ubicaciones)
TEST_IP = '187.188.133.8'  # Google DNS como ejemplo, cámbiala por la IP que quieras probar

# Función para obtener la ubicación desde una IP usando Nominatim
def get_location_from_ip(ip):
    try:
        # Primero obtenemos información de la IP
        response = requests.get(f'https://ipapi.co/{ip}/json/')
        if response.status_code == 200:
            ip_data = response.json()
            
            # Extraemos los datos del país y estado
            country = ip_data.get('country_name', 'Desconocido')
            region = ip_data.get('region', 'Desconocido')
            
            return {
                'country': country,
                'region': region
            }
        return {'country': 'Desconocido', 'region': 'Desconocido'}
    except Exception as e:
        print(f"Error obteniendo ubicación: {e}")
        return {'country': 'Desconocido', 'region': 'Desconocido'}

# Función para verificar la extensión del archivo
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS
def api_key_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        api_key = request.headers.get('X-API-KEY')
        if not api_key:
            return jsonify({"error": "API_KEY is missing"}), 401

        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        # Verificar si la API_KEY existe en la tabla Administradores o Clientes
        cursor.execute('SELECT * FROM Administradores WHERE api_key = %s', (api_key,))
        user = cursor.fetchone()

        if not user:
            cursor.execute('SELECT * FROM Clientes WHERE api_key = %s', (api_key,))
            user = cursor.fetchone()

        if user:
            # Verificar si la API_KEY ha expirado (por ejemplo, después de 24 horas)
            api_key_creation_time = user['api_key_created_at']
            if datetime.now() - api_key_creation_time > timedelta(hours=24):
                cursor.close()
                conn.close()
                return jsonify({"error": "API_KEY has expired"}), 403

        cursor.close()
        conn.close()

        if not user:
            return jsonify({"error": "Invalid API_KEY"}), 403

        return f(*args, **kwargs)
    return decorated_function

def generate_dynamic_api_key(user_id):
    # Combinar el ID del usuario con la fecha y hora actual
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    unique_string = f"{user_id}-{timestamp}"
    
    # Generar un hash único usando SHA-256
    api_key = hashlib.sha256(unique_string.encode()).hexdigest()
    return api_key

# Configura tu conexión a la base de datos
def get_db_connection():
    try:
        conn = mysql.connector.connect(
            host='libreria-db.cbnjujzklewo.us-east-1.rds.amazonaws.com',
            user='admin_libreria',  
            password='libreria123',  
            database='Libreria',
            port=3306  # Asegúrate de que es el puerto correcto
        )
        return conn
    except mysql.connector.Error as err:
        print(f"Error al conectar a la base de datos: {err}")
        return None
#Enviar correo de confirmacion al realizar la compra
def enviar_correo_confirmacion(cliente, libros, total, transaction_id):
    try:
        # Crear el cuerpo del correo
        subject = f"Confirmación de compra - Pedido #{transaction_id}"
        
        # Crear contenido HTML para el correo
        html_body = f"""
        <html>
            <body>
                <h2>¡Gracias por tu compra, {cliente['Nombre']}!</h2>
                <p>Tu pedido ha sido procesado exitosamente.</p>
                
                <h3>Detalles del pedido:</h3>
                <p><strong>Número de pedido:</strong> {transaction_id}</p>
                <p><strong>Fecha:</strong> {datetime.now().strftime('%d/%m/%Y %H:%M')}</p>
                <p><strong>Total:</strong> ${total:.2f} MXN</p>
                
                <h3>Productos:</h3>
                <table border="1" cellpadding="5" cellspacing="0">
                    <tr>
                        <th>Libro</th>
                        <th>Cantidad</th>
                        <th>Precio unitario</th>
                        <th>Subtotal</th>
                    </tr>
                    {"".join(
                        f"<tr><td>{libro['Nombre']}</td><td>{libro['Cantidad']}</td>"
                        f"<td>${libro['Precio']:.2f}</td><td>${libro['Cantidad'] * libro['Precio']:.2f}</td></tr>"
                        for libro in libros
                    )}
                </table>
                
                <h3>Información de envío:</h3>
                <p>{cliente['Nombre']} {cliente['Apellidos']}</p>
                <p>{cliente['Calle']} {cliente['NumExterior']}</p>
                <p>{cliente['Colonia']}, CP {cliente['CP']}</p>
                
                <p>Si tienes alguna pregunta, no dudes en contactarnos.</p>
                <p>Atentamente,<br>El equipo de Librería UTEZ</p>
            </body>
        </html>
        """
        
        # Crear el mensaje
        msg = Message(
            subject=subject,
            recipients=[cliente['Email']],
            html=html_body
        )
        
        # Enviar el correo
        mail.send(msg)
        return True
    except Exception as e:
        app.logger.error(f"Error al enviar correo: {str(e)}")
        return False

# Endpoint para obtener la ubicación por IP
@app.route('/get_location')
def get_location():
    # En producción usaríamos la IP real del cliente
    # client_ip = request.remote_addr
    
    # Para pruebas, usamos la IP de prueba configurada
    client_ip = TEST_IP 
    
    location = get_location_from_ip(client_ip)
    return jsonify(location)

@app.route('/ruta-protegida')
@api_key_required
def ruta_protegida():
    return jsonify({"message": "Acceso concedido a la ruta protegida"})

# Página principal con los botones de inicio de sesión y crear cuenta
@app.route('/')
def home():
    return render_template('home.html')

@app.route('/regenerar-api-key', methods=['POST'])
@api_key_required
def regenerar_api_key():
    if 'usuario' in session:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        if session['tipo_usuario'] == 'admin':
            new_api_key = generate_dynamic_api_key(session['IDpersonal'])
            cursor.execute('UPDATE Administradores SET api_key = %s, api_key_created_at = NOW() WHERE IDpersonal = %s', (new_api_key, session['IDpersonal']))
        else:
            new_api_key = generate_dynamic_api_key(session['idClientes'])
            cursor.execute('UPDATE Clientes SET api_key = %s, api_key_created_at = NOW() WHERE idClientes = %s', (new_api_key, session['idClientes']))

        conn.commit()
        cursor.close()
        conn.close()

        session['api_key'] = new_api_key
        return jsonify({"message": "API_KEY regenerada exitosamente", "api_key": new_api_key})

    return jsonify({"error": "No autorizado"}), 401


# Página de inicio de sesión
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        usuario = request.form['usuario']
        contrasena = request.form['contrasena']

        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        # Verificar si el usuario existe en la tabla Administradores
        cursor.execute('SELECT * FROM Administradores WHERE Usuario = %s AND Contrasena = %s', (usuario, contrasena))
        user = cursor.fetchone()

        if user:
            # Generar una nueva API_KEY dinámica
            new_api_key = generate_dynamic_api_key(user['IDpersonal'])
            
            # Actualizar la API_KEY en la base de datos
            cursor.execute('UPDATE Administradores SET api_key = %s WHERE IDpersonal = %s', (new_api_key, user['IDpersonal']))
            conn.commit()

            # Guardar datos en la sesión
            session['usuario'] = usuario
            session['tipo_usuario'] = 'admin'
            session['api_key'] = new_api_key

            cursor.close()
            conn.close()

            # Redirigir al área de administración
            return redirect(url_for('index'))  # Cambia 'index' por la ruta que desees para administradores

        else:
            flash('Credenciales incorrectas, por favor intenta nuevamente.', 'danger')
            cursor.close()
            conn.close()
            return redirect(url_for('login'))

    return render_template('login.html')  # Página de login

# Página de inicio de sesión para clientes
@app.route('/login_cliente', methods=['GET', 'POST'])
def login_cliente():
    if request.method == 'POST':
        usuario = request.form['usuario']
        contrasena = request.form['contrasena']

        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        # Verificar si el usuario existe en la tabla Clientes
        cursor.execute('SELECT * FROM Clientes WHERE Usuario = %s AND Contrasena = %s', (usuario, contrasena))
        user = cursor.fetchone()

        if user:
            # Generar una nueva API_KEY dinámica
            new_api_key = generate_dynamic_api_key(user['idClientes'])
            
            # Actualizar la API_KEY en la base de datos
            cursor.execute('UPDATE Clientes SET api_key = %s WHERE idClientes = %s', (new_api_key, user['idClientes']))
            conn.commit()

            # Guardar datos en la sesión
            session['usuario'] = usuario
            session['id_cliente'] = user['idClientes']
            session['nombre_cliente'] = user['Nombre']
            session['tipo_usuario'] = 'cliente'
            session['api_key'] = new_api_key

            cursor.close()
            conn.close()

            # Redirigir al catálogo de libros
            return redirect(url_for('catalogo'))  # Cambia 'catalogo' por la ruta que desees para clientes

        else:
            flash('Credenciales incorrectas, por favor intenta nuevamente.', 'danger')
            cursor.close()
            conn.close()
            return redirect(url_for('login_cliente'))

    return render_template('login_cliente.html') # Página de login para clientes

# Página para crear una nueva cuenta
@app.route('/crear-cuenta')
def crear_cuenta():
    return render_template('crear_cuenta.html')

# Ruta para registrar un nuevo cliente
@app.route('/registrar', methods=['POST'])
def registrar():
    nombre = request.form['nombre']
    apellidos = request.form['apellidos']
    email = request.form['email']
    usuario = request.form['usuario']
    contrasena = request.form['contrasena']
    calle = request.form['calle']
    colonia = request.form['colonia']
    cp = request.form['cp']
    num_exterior = request.form['num_exterior']
    num_interior = request.form['num_interior']
    num_contacto = request.form['num_contacto']

    # Conexión a la base de datos
    conn = get_db_connection()
    cursor = conn.cursor()

    # Insertar los datos en la tabla Direcciones primero
    cursor.execute("""
        INSERT INTO Direcciones (Calle, Colonia, CP, NumExterior, NumInterior, NumContacto)
        VALUES (%s, %s, %s, %s, %s, %s)
    """, (calle, colonia, cp, num_exterior, num_interior, num_contacto))

    # Obtener el ID de la dirección insertada
    direccion_id = cursor.lastrowid

    # Insertar el nuevo cliente
    cursor.execute("""
        INSERT INTO Clientes (Nombre, Apellidos, Email, Usuario, Contrasena, IDireccion)
        VALUES (%s, %s, %s, %s, %s, %s)
    """, (nombre, apellidos, email, usuario, contrasena, direccion_id))

    conn.commit()
    cursor.close()
    conn.close()

    flash('Cuenta creada exitosamente, ya puedes iniciar sesión.', 'success')
    return redirect(url_for('login_cliente'))  # Redirigir al login de cliente después de registrar
# Ruta para gestionar clientes (solo para administradores)
# Ruta para gestionar clientes (solo para administradores)
@app.route('/gestionar-clientes')
def gestionar_clientes():
    if 'usuario' not in session or session.get('tipo_usuario') != 'admin':
        return redirect(url_for('login'))

    # Conexión a la base de datos
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    # Obtener todos los clientes con su dirección
    cursor.execute('''
        SELECT c.*, d.Calle, d.Colonia, d.CP, d.NumExterior, d.NumInterior, d.NumContacto 
        FROM Clientes c 
        JOIN Direcciones d ON c.IDireccion = d.idDirecciones
    ''')
    clientes = cursor.fetchall()

    cursor.close()
    conn.close()

    return render_template('gestionar_clientes.html', clientes=clientes)

# Ruta para agregar un nuevo cliente (solo para administradores)
@app.route('/agregar-cliente')
def agregar_cliente():
    if 'usuario' not in session or session.get('tipo_usuario') != 'admin':
        return redirect(url_for('login'))

    return render_template('crear_cuenta.html')
# Ruta para eliminar un cliente (solo para administradores)
@app.route('/eliminar-cliente/<int:id>', methods=['GET'])
def eliminar_cliente(id):
    if 'usuario' not in session or session.get('tipo_usuario') != 'admin':
        return redirect(url_for('login'))

    conn = get_db_connection()
    cursor = conn.cursor()

    # Eliminar el cliente y su dirección asociada
    cursor.execute('DELETE FROM Clientes WHERE idClientes = %s', (id,))
    cursor.execute('DELETE FROM Direcciones WHERE idDirecciones = (SELECT IDireccion FROM Clientes WHERE idClientes = %s)', (id,))

    conn.commit()
    cursor.close()
    conn.close()

    flash('Cliente eliminado exitosamente.', 'success')
    return redirect(url_for('gestionar_clientes'))
# Ruta para editar un cliente (solo para administradores)
@app.route('/editar-cliente/<int:id>', methods=['GET', 'POST'])
def editar_cliente(id):
    # Verificar que el usuario sea un administrador
    if 'usuario' not in session or session.get('tipo_usuario') != 'admin':
        return redirect(url_for('login'))

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    if request.method == 'POST':
        # Obtener datos del formulario
        nombre = request.form['nombre']
        apellidos = request.form['apellidos']
        email = request.form['email']
        usuario = request.form['usuario']
        contrasena = request.form.get('contrasena', '')
        calle = request.form['calle']
        colonia = request.form['colonia']
        cp = request.form['cp']
        num_exterior = request.form['num_exterior']
        num_interior = request.form['num_interior']
        num_contacto = request.form['num_contacto']

        # Actualizar la dirección
        cursor.execute('''
            UPDATE Direcciones 
            SET Calle = %s, Colonia = %s, CP = %s, NumExterior = %s, NumInterior = %s, NumContacto = %s
            WHERE idDirecciones = (SELECT IDireccion FROM Clientes WHERE idClientes = %s)
        ''', (calle, colonia, cp, num_exterior, num_interior, num_contacto, id))

        # Actualizar el cliente
        if contrasena:
            cursor.execute('''
                UPDATE Clientes 
                SET Nombre = %s, Apellidos = %s, Email = %s, Usuario = %s, Contrasena = %s 
                WHERE idClientes = %s
            ''', (nombre, apellidos, email, usuario, contrasena, id))
        else:
            cursor.execute('''
                UPDATE Clientes 
                SET Nombre = %s, Apellidos = %s, Email = %s, Usuario = %s 
                WHERE idClientes = %s
            ''', (nombre, apellidos, email, usuario, id))

        conn.commit()
        cursor.close()
        conn.close()

        # Mostrar mensaje de éxito y redirigir a la gestión de clientes
        flash('Cliente actualizado exitosamente.', 'success')
        return redirect(url_for('gestionar_clientes'))

    # Obtener los datos del cliente a editar
    cursor.execute('''
        SELECT c.*, d.Calle, d.Colonia, d.CP, d.NumExterior, d.NumInterior, d.NumContacto 
        FROM Clientes c 
        JOIN Direcciones d ON c.IDireccion = d.idDirecciones
        WHERE c.idClientes = %s
    ''', (id,))
    cliente = cursor.fetchone()

    cursor.close()
    conn.close()

    # Renderizar la plantilla de edición
    return render_template('editar_cliente.html', cliente=cliente)
# Catálogo de libros para clientes
@app.route('/catalogo')
def catalogo():
    if 'usuario' not in session or session.get('tipo_usuario') != 'cliente':
        return redirect(url_for('login_cliente'))
    
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM Libro")
    libros = cursor.fetchall()
    cursor.close()
    conn.close()

    # Obtener la ubicación para pasar al template
    # En producción usaríamos la IP real del cliente
    # client_ip = request.remote_addr
    
    # Para pruebas, usamos la IP de prueba configurada
    client_ip = TEST_IP
    location = get_location_from_ip(client_ip)

    return render_template('catalogo_cliente.html', libros=libros, location=location)

# Detalle de un libro
@app.route('/libro/<int:id>')
def detalle_libro(id):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    # Obtener los detalles del libro
    cursor.execute('SELECT * FROM Libro WHERE idLibro = %s', (id,))
    libro = cursor.fetchone()

    # Obtener las reseñas del libro
    cursor.execute('''
        SELECT r.*, c.Nombre AS nombre_cliente 
        FROM Resenas r 
        JOIN Clientes c ON r.idCliente = c.idClientes 
        WHERE r.idLibro = %s
    ''', (id,))
    resenas = cursor.fetchall()

    cursor.close()
    conn.close()

    if not libro:
        flash("Libro no encontrado.", "danger")
        return redirect(url_for('catalogo'))

    return render_template('detalle_libro.html', libro=libro, resenas=resenas)

# Calificar libro
@app.route('/calificar/<int:id_libro>', methods=['POST'])
def calificar_libro(id_libro):
    if 'usuario' not in session or session.get('tipo_usuario') != 'cliente':
        return redirect(url_for('login_cliente'))
    
    calificacion = int(request.form['calificacion'])
    comentario = request.form.get('comentario', '')
    id_cliente = session.get('id_cliente')
    
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    # Verificar si el usuario ya ha calificado este libro
    cursor.execute('SELECT * FROM Resenas WHERE idLibro = %s AND idCliente = %s', 
                  (id_libro, id_cliente))
    resena_existente = cursor.fetchone()
    
    if resena_existente:
        # Actualizar la reseña existente
        cursor.execute('''
            UPDATE Resenas 
            SET Calificacion = %s, Comentario = %s, FechaCreacion = NOW() 
            WHERE idLibro = %s AND idCliente = %s
        ''', (calificacion, comentario, id_libro, id_cliente))
        flash('Has actualizado tu reseña exitosamente.', 'success')
    else:
        # Crear una nueva reseña
        cursor.execute('''
            INSERT INTO Resenas (idLibro, idCliente, Calificacion, Comentario) 
            VALUES (%s, %s, %s, %s)
        ''', (id_libro, id_cliente, calificacion, comentario))
        flash('Has calificado el libro exitosamente.', 'success')
    
    conn.commit()
    cursor.close()
    conn.close()
    
    return redirect(url_for('detalle_libro', id=id_libro))

# Perfil del cliente
@app.route('/perfil')
def perfil_cliente():
    if 'usuario' not in session or session.get('tipo_usuario') != 'cliente':
        return redirect(url_for('login_cliente'))
    
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    # Obtener información del cliente y su dirección
    cursor.execute('''
        SELECT c.*, d.* 
        FROM Clientes c 
        JOIN Direcciones d ON c.IDireccion = d.idDirecciones 
        WHERE c.idClientes = %s
    ''', (session.get('id_cliente'),))
    
    cliente = cursor.fetchone()
    
    # Obtener todas las direcciones del cliente
    cursor.execute('SELECT * FROM Direcciones WHERE idClientes = %s', (session.get('id_cliente'),))
    direcciones = cursor.fetchall()
    
    cursor.close()
    conn.close()
    
    return render_template('perfil_cliente.html', cliente=cliente, direcciones=direcciones)

# Actualizar perfil del cliente
@app.route('/actualizar-perfil', methods=['POST'])
def actualizar_perfil():
    if 'usuario' not in session or session.get('tipo_usuario') != 'cliente':
        return redirect(url_for('login_cliente'))
    
    # Datos del cliente
    nombre = request.form['nombre']
    apellidos = request.form['apellidos']
    email = request.form['email']
    usuario = request.form['usuario']
    contrasena = request.form.get('contrasena', '')
    
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    # Actualizar datos del cliente
    if contrasena:
        cursor.execute('''
            UPDATE Clientes 
            SET Nombre = %s, Apellidos = %s, Email = %s, Usuario = %s, Contrasena = %s 
            WHERE idClientes = %s
        ''', (nombre, apellidos, email, usuario, contrasena, session.get('id_cliente')))
    else:
        cursor.execute('''
            UPDATE Clientes 
            SET Nombre = %s, Apellidos = %s, Email = %s, Usuario = %s 
            WHERE idClientes = %s
        ''', (nombre, apellidos, email, usuario, session.get('id_cliente')))
    
    conn.commit()
    
    # Actualizar nombre de usuario en la sesión si cambió
    if session['usuario'] != usuario:
        session['usuario'] = usuario
        session['nombre_cliente'] = nombre
    
    cursor.close()
    conn.close()
    
    flash('Perfil actualizado exitosamente.', 'success')
    return redirect(url_for('perfil_cliente'))

@app.route('/agregar-direccion', methods=['GET', 'POST'])
def agregar_direccion():
    
    if 'usuario' not in session or session.get('tipo_usuario') != 'cliente':
        return redirect(url_for('login_cliente'))
    
    if request.method == 'POST':
        calle = request.form['calle']
        colonia = request.form['colonia']
        cp = request.form['cp']
        num_exterior = request.form['num_exterior']
        num_interior = request.form['num_interior']
        num_contacto = request.form['num_contacto']
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Insertar la nueva dirección
        cursor.execute('''
            INSERT INTO Direcciones (Calle, Colonia, CP, NumExterior, NumInterior, NumContacto, idClientes)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            ''', (calle, colonia, cp, num_exterior, num_interior, num_contacto, session.get('id_cliente')))
        
        conn.commit()
        cursor.close()
        conn.close()
        
        flash('Dirección agregada exitosamente.', 'success')
        return redirect(url_for('perfil_cliente'))
    
    return render_template('agregar_direccion.html')

@app.route('/editar-direccion/<int:id>', methods=['GET', 'POST'])
def editar_direccion(id):
    if 'usuario' not in session or session.get('tipo_usuario') != 'cliente':
        return redirect(url_for('login_cliente'))
    
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    if request.method == 'POST':
        calle = request.form['calle']
        colonia = request.form['colonia']
        cp = request.form['cp']
        num_exterior = request.form['num_exterior']
        num_interior = request.form['num_interior']
        num_contacto = request.form['num_contacto']
        
        # Actualizar la dirección
        cursor.execute('''
            UPDATE Direcciones 
            SET Calle = %s, Colonia = %s, CP = %s, NumExterior = %s, NumInterior = %s, NumContacto = %s
            WHERE idDirecciones = %s
        ''', (calle, colonia, cp, num_exterior, num_interior, num_contacto, id))
        
        conn.commit()
        cursor.close()
        conn.close()
        
        flash('Dirección actualizada exitosamente.', 'success')
        return redirect(url_for('perfil_cliente'))
    
    # Obtener la dirección a editar
    cursor.execute('SELECT * FROM Direcciones WHERE idDirecciones = %s', (id,))
    direccion = cursor.fetchone()
    
    cursor.close()
    conn.close()
    
    return render_template('editar_direccion.html', direccion=direccion)

@app.route('/eliminar-direccion/<int:id>', methods=['GET'])
def eliminar_direccion(id):
    if 'usuario' not in session or session.get('tipo_usuario') != 'cliente':
        return redirect(url_for('login_cliente'))
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Eliminar la dirección
    cursor.execute('DELETE FROM Direcciones WHERE idDirecciones = %s', (id,))
    conn.commit()
    
    cursor.close()
    conn.close()
    
    flash('Dirección eliminada exitosamente.', 'success')
    return redirect(url_for('perfil_cliente'))       

@app.route('/eliminar-cuenta', methods=['GET'])
def eliminar_cuenta():
    if 'usuario' not in session or session.get('tipo_usuario') != 'cliente':
        return redirect(url_for('login_cliente'))
    
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    # Eliminar la cuenta del cliente
    cursor.execute('DELETE FROM Clientes WHERE idClientes = %s', (session.get('id_cliente'),))
    conn.commit()
    
    cursor.close()
    conn.close()
    
    # Cerrar sesión
    session.pop('usuario', None)
    session.pop('tipo_usuario', None)
    session.pop('id_cliente', None)
    session.pop('nombre_cliente', None)
    
    flash('Tu cuenta ha sido eliminada exitosamente.', 'success')
    return redirect(url_for('home'))

# Página para gestionar los libros (CRUD)
@app.route('/index')
def index():
    if 'usuario' not in session:
        return redirect(url_for('login'))

    # Conexión a la base de datos
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    # Obtener todos los libros
    cursor.execute('SELECT * FROM Libro')
    libros = cursor.fetchall()

    cursor.close()
    conn.close()

    return render_template('index.html', libros=libros)

# Ruta para agregar un nuevo libro
@app.route('/agregar-libro', methods=['POST'])
def agregar_libro():
    if 'usuario' not in session or session.get('tipo_usuario') != 'admin':
        return redirect(url_for('login'))

    nombre = request.form['nombre']
    editorial = request.form['editorial']
    edicion = request.form['edicion']
    estado = request.form['estado']
    cantidad = int(request.form['cantidad'])
    precio = float(request.form['precio'])  # Nuevo campo: Precio

    # Manejo de la imagen
    if 'imagen' not in request.files:
        flash('No se ha seleccionado una imagen.', 'danger')
        return redirect(url_for('index'))

    file = request.files['imagen']
    if file.filename == '':
        flash('No se ha seleccionado una imagen.', 'danger')
        return redirect(url_for('index'))

    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
    else:
        flash('Formato de imagen no permitido.', 'danger')
        return redirect(url_for('index'))

    # Conexión a la base de datos
    conn = get_db_connection()
    cursor = conn.cursor()

    # Insertar el nuevo libro con la ruta de la imagen y el precio
    cursor.execute("""
        INSERT INTO Libro (Nombre, Editorial, Edicion, Estado, Cantidad, Precio, FechaCreacion, Imagen)
        VALUES (%s, %s, %s, %s, %s, %s, NOW(), %s)
    """, (nombre, editorial, edicion, estado, cantidad, precio, filename))

    conn.commit()
    cursor.close()
    conn.close()

    flash('Libro agregado exitosamente.', 'success')
    return redirect(url_for('index'))

# Ruta para editar un libro
@app.route('/editar-libro/<int:id>', methods=['GET', 'POST'])
def editar_libro(id):
    if 'usuario' not in session or session.get('tipo_usuario') != 'admin':
        return redirect(url_for('login'))

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    if request.method == 'POST':
        nombre = request.form['nombre']
        editorial = request.form['editorial']
        edicion = request.form['edicion']
        estado = request.form['estado']
        cantidad = request.form['cantidad']

        # Actualizar el libro
        cursor.execute("""
            UPDATE Libro
            SET Nombre = %s, Editorial = %s, Edicion = %s, Estado = %s, Cantidad = %s
            WHERE idLibro = %s
        """, (nombre, editorial, edicion, estado, cantidad, id))

        conn.commit()
        cursor.close()
        conn.close()

        flash('Libro actualizado exitosamente.', 'success')
        return redirect(url_for('index'))

    # Obtener los datos del libro a editar
    cursor.execute('SELECT * FROM Libro WHERE idLibro = %s', (id,))
    libro = cursor.fetchone()

    cursor.close()
    conn.close()

    return render_template('editar_libro.html', libro=libro)

# Ruta para eliminar un libro
@app.route('/eliminar-libro/<int:id>', methods=['GET'])
def eliminar_libro(id):
    if 'usuario' not in session or session.get('tipo_usuario') != 'admin':
        return redirect(url_for('login'))

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)  # Usar dictionary=True para obtener resultados como diccionarios

    # Obtener la ruta de la imagen antes de eliminar el libro
    cursor.execute('SELECT Imagen FROM Libro WHERE idLibro = %s', (id,))
    libro = cursor.fetchone()  # Ahora libro es un diccionario, no una tupla

    if libro and libro['Imagen']:  # Acceder a la clave 'Imagen' del diccionario
        # Eliminar la imagen del servidor
        try:
            os.remove(os.path.join(app.config['UPLOAD_FOLDER'], libro['Imagen']))
        except Exception as e:
            print(f"Error al eliminar la imagen: {e}")

    # Eliminar el libro
    cursor.execute('DELETE FROM Libro WHERE idLibro = %s', (id,))
    conn.commit()

    cursor.close()
    conn.close()

    flash('Libro eliminado exitosamente.', 'success')
    return redirect(url_for('index'))

# Ruta para cerrar sesión
@app.route('/logout')
def logout():
    session.pop('usuario', None)
    session.pop('tipo_usuario', None)
    session.pop('id_cliente', None)
    session.pop('nombre_cliente', None)
    flash('Has cerrado sesión exitosamente.', 'success')
    return redirect(url_for('home'))

# Ruta para cerrar sesión de cliente
@app.route('/logout_cliente')
def logout_cliente():
    session.pop('usuario', None)
    session.pop('tipo_usuario', None)
    session.pop('id_cliente', None)
    session.pop('nombre_cliente', None)
    flash('Has cerrado sesión exitosamente.', 'success')
    return redirect(url_for('home'))

#####
@app.route('/agregar_al_carrito/<int:id_libro>', methods=['POST'])
def agregar_al_carrito(id_libro):
    if 'usuario' not in session or session.get('tipo_usuario') != 'cliente':
        return redirect(url_for('login_cliente'))

    try:
        cantidad = int(request.form['cantidad'])
        id_cliente = session.get('id_cliente')

        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        # 1. Verificar stock disponible
        cursor.execute('SELECT Cantidad, Estado FROM Libro WHERE idLibro = %s', (id_libro,))
        libro = cursor.fetchone()
        
        if not libro or libro['Estado'] == 'NoStock':
            flash('Este libro no está disponible actualmente', 'danger')
            return redirect(url_for('catalogo'))

        # 2. Verificar si ya está en el carrito
        cursor.execute('SELECT Cantidad FROM Carrito WHERE idCliente = %s AND idLibro = %s', (id_cliente, id_libro))
        item = cursor.fetchone()
        
        cantidad_total = cantidad + (item['Cantidad'] if item else 0)
        
        if cantidad_total > libro['Cantidad']:
            flash(f'No hay suficiente stock. Disponible: {libro["Cantidad"]}', 'warning')
            return redirect(url_for('catalogo'))

        # 3. Agregar/actualizar en carrito
        if item:
            cursor.execute('''
                UPDATE Carrito 
                SET Cantidad = %s 
                WHERE idCliente = %s AND idLibro = %s
            ''', (cantidad_total, id_cliente, id_libro))
        else:
            cursor.execute('''
                INSERT INTO Carrito (idCliente, idLibro, Cantidad, Precio)
                SELECT %s, %s, %s, Precio FROM Libro WHERE idLibro = %s
            ''', (id_cliente, id_libro, cantidad, id_libro))

        conn.commit()
        flash('Libro agregado al carrito', 'success')

    except ValueError:
        flash('Cantidad inválida', 'danger')
    except Exception as e:
        conn.rollback()
        flash(f'Error: {str(e)}', 'danger')
    finally:
        cursor.close()
        conn.close()

    return redirect(url_for('catalogo'))
####

@app.route('/carrito')
def ver_carrito():
    if 'usuario' not in session or session.get('tipo_usuario') != 'cliente':
        return redirect(url_for('login_cliente'))

    id_cliente = session.get('id_cliente')
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    # Asegúrate de que esta consulta devuelve los datos correctamente
    cursor.execute('''
        SELECT l.idLibro, l.Nombre, c.Cantidad, l.Precio, l.Cantidad as StockDisponible
        FROM Carrito c 
        JOIN Libro l ON c.idLibro = l.idLibro 
        WHERE c.idCliente = %s
    ''', (id_cliente,))
    
    libros = cursor.fetchall()  # Esta línea es crucial
    total = sum(libro['Cantidad'] * libro['Precio'] for libro in libros)

    cursor.close()
    conn.close()

    # Debug: Verifica qué estás pasando al template
    print("Libros en carrito:", libros)
    print("Total calculado:", total)

    return render_template('carrito.html', libros=libros, total=total)
####

@app.route('/eliminar_del_carrito/<int:id_libro>', methods=['POST'])
def eliminar_del_carrito(id_libro):
    if 'usuario' not in session or session.get('tipo_usuario') != 'cliente':
        return redirect(url_for('login_cliente'))

    id_cliente = session.get('id_cliente')

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute('DELETE FROM Carrito WHERE idCliente = %s AND idLibro = %s', (id_cliente, id_libro))
    conn.commit()

    cursor.close()
    conn.close()

    flash('Libro eliminado del carrito exitosamente.', 'success')
    return redirect(url_for('ver_carrito'))

###

@app.route('/actualizar_carrito/<int:id_libro>', methods=['POST'])
def actualizar_carrito(id_libro):
    if 'usuario' not in session or session.get('tipo_usuario') != 'cliente':
        return redirect(url_for('login_cliente'))

    try:
        nueva_cantidad = int(request.form['cantidad'])
        id_cliente = session.get('id_cliente')

        if nueva_cantidad <= 0:
            flash('La cantidad debe ser mayor a cero', 'danger')
            return redirect(url_for('ver_carrito'))

        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        # 1. Verificar stock disponible
        cursor.execute('SELECT Cantidad FROM Libro WHERE idLibro = %s', (id_libro,))
        stock_disponible = cursor.fetchone()['Cantidad']
        
        if nueva_cantidad > stock_disponible:
            flash(f'No hay suficiente stock. Disponible: {stock_disponible}', 'warning')
            return redirect(url_for('ver_carrito'))

        # 2. Actualizar carrito
        cursor.execute('''
            UPDATE Carrito 
            SET Cantidad = %s 
            WHERE idCliente = %s AND idLibro = %s
        ''', (nueva_cantidad, id_cliente, id_libro))

        conn.commit()
        flash('Cantidad actualizada', 'success')

    except ValueError:
        flash('Cantidad inválida', 'danger')
    except Exception as e:
        conn.rollback()
        flash(f'Error: {str(e)}', 'danger')
    finally:
        cursor.close()
        conn.close()

    return redirect(url_for('ver_carrito'))
#####
# Configuración PayPal (al inicio del archivo)
PAYPAL_EMAIL = "sb-7whvk39219925@business.example.com"  # Email de tu cuenta Sandbox Business
PAYPAL_SANDBOX = True  # Cambiar a False en producción

# Ruta para comprar carrito (simplificada)
@app.route('/comprar_carrito', methods=['POST'])
def comprar_carrito():
    """Prepara los datos para PayPal (ahora manejado directamente desde el formulario en carrito.html)"""
    if 'usuario' not in session or session.get('tipo_usuario') != 'cliente':
        return redirect(url_for('login_cliente'))

    # Esta lógica ahora se maneja en el frontend y PayPal
    # Solo redirigimos si hay algún problema
    flash('Por favor usa el botón de PayPal para completar tu compra', 'info')
    return redirect(url_for('ver_carrito'))

# Ruta para compra exitosa    
@app.route('/compra_exitosa')
def compra_exitosa():
    """Maneja la respuesta exitosa de PayPal y envía correo de confirmación"""
    # Verificar si es un retorno exitoso
    if request.args.get('success') != 'true':
        flash('No se recibió confirmación de pago', 'danger')
        return redirect(url_for('ver_carrito'))

    # Obtener parámetros de PayPal
    transaction_id = request.args.get('tx') or request.args.get('transaction_id')
    payment_amount = request.args.get('amt') or request.args.get('payment_amount')
    currency = request.args.get('cc') or request.args.get('currency_code')
    
    if not transaction_id:
        # Generar un ID temporal si no viene de PayPal
        transaction_id = str(uuid.uuid4())
        flash('Advertencia: No se recibió ID de transacción de PayPal. Se generó uno temporal.', 'warning')

    # Obtener datos del cliente
    if 'usuario' not in session or session.get('tipo_usuario') != 'cliente':
        return redirect(url_for('login_cliente'))

    id_cliente = session.get('id_cliente')
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    try:
        # 1. Obtener items del carrito
        cursor.execute('''
            SELECT c.idLibro, l.Nombre, c.Cantidad, l.Precio, l.Editorial
            FROM Carrito c 
            JOIN Libro l ON c.idLibro = l.idLibro 
            WHERE c.idCliente = %s
        ''', (id_cliente,))
        libros = cursor.fetchall()

        if not libros:
            flash('No hay items en el carrito', 'warning')
            return redirect(url_for('ver_carrito'))

        # 2. Calcular total
        total = sum(libro['Cantidad'] * libro['Precio'] for libro in libros)

        # 3. Registrar cada libro vendido
        for libro in libros:
            cursor.execute('''
                INSERT INTO Ventas (
                    Fecha, ID_libro, IDClientes, Cantidad, 
                    PrecioUnitario, Total, MetodoPago, TransactionID, Estado
                ) VALUES (
                    NOW(), %s, %s, %s, %s, %s, 'PayPal', %s, 'Completado'
                )
            ''', (
                libro['idLibro'], id_cliente, libro['Cantidad'],
                libro['Precio'], libro['Cantidad'] * libro['Precio'], transaction_id
            ))

            # Actualizar inventario
            cursor.execute('''
                UPDATE Libro 
                SET Cantidad = Cantidad - %s,
                    Estado = CASE WHEN (Cantidad - %s) <= 0 THEN 'NoStock' ELSE 'Stock' END
                WHERE idLibro = %s
            ''', (libro['Cantidad'], libro['Cantidad'], libro['idLibro']))

        # 4. Vaciar carrito
        cursor.execute('DELETE FROM Carrito WHERE idCliente = %s', (id_cliente,))
        
        # 5. Registrar transacción PayPal
        cursor.execute('''
            INSERT INTO TransaccionesPayPal (
                transaction_id, id_cliente, monto, moneda, estado, fecha
            ) VALUES (
                %s, %s, %s, %s, 'Completado', NOW()
            )
        ''', (transaction_id, id_cliente, payment_amount or total, currency or 'MXN'))

        # 6. Obtener datos completos del cliente para el correo
        cursor.execute('''
            SELECT c.*, d.Calle, d.NumExterior, d.Colonia, d.CP, d.NumContacto
            FROM Clientes c
            JOIN Direcciones d ON c.IDireccion = d.idDirecciones
            WHERE c.idClientes = %s
        ''', (id_cliente,))
        cliente_data = cursor.fetchone()

        conn.commit()

        # 7. Enviar correo de confirmación
        try:
            # Crear el cuerpo del correo
            subject = f"Confirmación de compra - Pedido #{transaction_id}"
            
            # Crear contenido HTML para el correo
            html_body = render_template(
                'email_confirmacion.html',
                cliente=cliente_data,
                libros=libros,
                total=total,
                transaction_id=transaction_id,
                fecha=datetime.now().strftime('%d/%m/%Y %H:%M')
            )
            
            # Crear el mensaje
            msg = Message(
                subject=subject,
                recipients=[cliente_data['Email']],
                html=html_body,
                sender=app.config['MAIL_DEFAULT_SENDER']
            )
            
            # Enviar el correo (en segundo plano para no bloquear la respuesta)
            mail.send(msg)
            app.logger.info(f"Correo de confirmación enviado a {cliente_data['Email']}")
        except Exception as email_error:
            app.logger.error(f"Error al enviar correo: {str(email_error)}")
            # No fallar la compra solo por error de correo

        return render_template('resumen_compra.html', 
                            libros=libros,
                            total=total,
                            cliente=cliente_data,
                            direccion=cliente_data,
                            paypal_data={
                                'transaction_id': transaction_id,
                                'payment_amount': payment_amount or total,
                                'currency': currency or 'MXN',
                                'status': 'Completado'
                            })

    except Exception as e:
        conn.rollback()
        app.logger.error(f"Error en compra_exitosa: {str(e)}")
        flash('Ocurrió un error al procesar tu compra', 'danger')
        return redirect(url_for('ver_carrito'))
    finally:
        cursor.close()
        conn.close()

# Ruta para IPN (Opcional pero recomendado)
@app.route('/ipn_paypal', methods=['POST'])
def ipn_paypal():
    """Endpoint para verificación de pagos con IPN"""
    # Implementar lógica de verificación IPN para producción
    # Esto es importante para verificar que los pagos son reales
    return '', 200

@lru_cache(maxsize=1)
def load_menus():
    try:
        with open('menus.yaml', 'r', encoding='utf-8') as file:
            menu_data = yaml.safe_load(file)
            return menu_data.get('menus', [])
    except FileNotFoundError:
        return []
    except yaml.YAMLError as e:
        app.logger.error(f"Error al cargar menus.yaml: {e}")
        return []

@app.context_processor
def inject_menus():
    menus = load_menus()
    filtered_menus = []
    for menu in menus:
        if menu.get('visible', True):
            if menu.get('admin_only', False):
                if 'usuario' in session and session.get('tipo_usuario') == 'admin':
                    filtered_menus.append(menu)
            else:
                filtered_menus.append(menu)
    return dict(global_menus=filtered_menus)

@app.route('/admin/menus', methods=['GET', 'POST'])
def admin_menus():
    if 'usuario' not in session or session.get('tipo_usuario') != 'admin':
        return redirect(url_for('login'))

    form = MenuForm()
    menus = load_menus()

    if form.validate_on_submit():
        new_menu = {
            'name': form.name.data,
            'url': form.url.data,
            'icon': form.icon.data or 'bi-link',
            'visible': form.visible.data,
            'admin_only': form.admin_only.data
        }
        menus.append(new_menu)
        
        try:
            with open('menus.yaml', 'w', encoding='utf-8') as file:
                yaml.dump({'menus': menus}, file, allow_unicode=True)
            load_menus.cache_clear()
            flash('Menú actualizado correctamente', 'success')
        except Exception as e:
            app.logger.error(f"Error al guardar menus.yaml: {e}")
            flash('Error al guardar los cambios', 'danger')

        return redirect(url_for('admin_menus'))

    return render_template('admin_menus.html', menus=menus, form=form)

@app.route('/admin/menus/delete/<int:index>', methods=['POST'])
def delete_menu(index):
    if 'usuario' not in session or session.get('tipo_usuario') != 'admin':
        return redirect(url_for('login'))

    menus = load_menus()
    if 0 <= index < len(menus):
        deleted_name = menus[index]['name']
        del menus[index]
        
        try:
            with open('menus.yaml', 'w', encoding='utf-8') as file:
                yaml.dump({'menus': menus}, file, allow_unicode=True)
            load_menus.cache_clear()
            flash(f'Menú "{deleted_name}" eliminado', 'success')
        except Exception as e:
            app.logger.error(f"Error al guardar menus.yaml: {e}")
            flash('Error al eliminar el menú', 'danger')

    return redirect(url_for('admin_menus'))
if __name__ == '__main__':
    app.run(debug=True)