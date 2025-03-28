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


app = Flask(__name__)
app.secret_key = 'your_secret_key'  # Necesario para usar sesiones

# Configuración de Flask-Mail
app.config['MAIL_SERVER'] = 'smtp.gmail.com'  # Servidor SMTP de Gmail
app.config['MAIL_PORT'] = 587  # Puerto para TLS
app.config['MAIL_USE_TLS'] = True  # Usar TLS
app.config['MAIL_USERNAME'] = '20203tn110@utez.edu.mx'  # Tu correo electrónico
app.config['MAIL_PASSWORD'] = 'Sanandres200245'  # Tu contraseña de correo
app.config['MAIL_DEFAULT_SENDER'] = '20203tn110@utez.edu.mx'  # Correo remitente

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
            host='localhost',
            user='root',  
            password='root',  
            database='Libreria',
            port=3306  # Asegúrate de que es el puerto correcto
        )
        return conn
    except mysql.connector.Error as err:
        print(f"Error al conectar a la base de datos: {err}")
        return None

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

        # 1. Verificar existencia y precio actual del libro
        cursor.execute('''
            SELECT Precio, Cantidad FROM Libro 
            WHERE idLibro = %s AND Estado = "Stock"
        ''', (id_libro,))
        libro = cursor.fetchone()

        if not libro:
            flash('El libro no está disponible', 'danger')
            return redirect(url_for('catalogo'))

        # 2. Verificar stock suficiente
        if libro['Cantidad'] < cantidad:
            flash('No hay suficiente stock disponible', 'warning')
            return redirect(url_for('catalogo'))

        # 3. Verificar si ya está en el carrito
        cursor.execute('''
            SELECT idCarrito, Cantidad FROM Carrito 
            WHERE idCliente = %s AND idLibro = %s
        ''', (id_cliente, id_libro))
        item = cursor.fetchone()

        if item:
            # Actualizar cantidad y precio (por si cambió)
            nueva_cantidad = item['Cantidad'] + cantidad
            cursor.execute('''
                UPDATE Carrito 
                SET Cantidad = %s, Precio = %s 
                WHERE idCarrito = %s
            ''', (nueva_cantidad, libro['Precio'], item['idCarrito']))
        else:
            # Insertar nuevo item con precio actual
            cursor.execute('''
                INSERT INTO Carrito (idCliente, idLibro, Cantidad, Precio)
                VALUES (%s, %s, %s, %s)
            ''', (id_cliente, id_libro, cantidad, libro['Precio']))

        conn.commit()
        flash('Libro agregado al carrito correctamente', 'success')

    except ValueError:
        flash('Cantidad inválida', 'danger')
    except Exception as e:
        conn.rollback()
        flash(f'Error al agregar al carrito: {str(e)}', 'danger')
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

    # Obtener los libros en el carrito con su ID, nombre, cantidad y precio
    cursor.execute('''
        SELECT l.idLibro, l.Nombre, c.Cantidad, l.Precio 
        FROM Carrito c 
        JOIN Libro l ON c.idLibro = l.idLibro 
        WHERE c.idCliente = %s
    ''', (id_cliente,))
    libros = cursor.fetchall()

    # Calcular el total de la compra
    total = sum(libro['Cantidad'] * libro['Precio'] for libro in libros)

    cursor.close()
    conn.close()

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
        cantidad = int(request.form['cantidad'])
        id_cliente = session.get('id_cliente')

        if cantidad <= 0:
            flash('La cantidad debe ser mayor a cero', 'danger')
            return redirect(url_for('ver_carrito'))

        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        # 1. Verificar stock disponible
        cursor.execute('''
            SELECT Cantidad FROM Libro 
            WHERE idLibro = %s AND Estado = "Stock"
        ''', (id_libro,))
        libro = cursor.fetchone()

        if not libro or libro['Cantidad'] < cantidad:
            flash('No hay suficiente stock disponible', 'warning')
            return redirect(url_for('ver_carrito'))

        # 2. Obtener precio actual
        cursor.execute('SELECT Precio FROM Libro WHERE idLibro = %s', (id_libro,))
        precio_actual = cursor.fetchone()['Precio']

        # 3. Actualizar carrito con cantidad y precio actualizado
        cursor.execute('''
            UPDATE Carrito 
            SET Cantidad = %s, Precio = %s
            WHERE idCliente = %s AND idLibro = %s
        ''', (cantidad, precio_actual, id_cliente, id_libro))

        conn.commit()
        flash('Cantidad actualizada correctamente', 'success')

    except ValueError:
        flash('Cantidad inválida', 'danger')
    except Exception as e:
        conn.rollback()
        flash(f'Error al actualizar: {str(e)}', 'danger')
    finally:
        cursor.close()
        conn.close()

    return redirect(url_for('ver_carrito'))
#####
@app.route('/comprar_carrito', methods=['POST'])
def comprar_carrito():
    if 'usuario' not in session or session.get('tipo_usuario') != 'cliente':
        return redirect(url_for('login_cliente'))

    id_cliente = session.get('id_cliente')

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    # 1. VALIDAR CARRITO VACÍO
    cursor.execute('SELECT COUNT(*) as total_items FROM Carrito WHERE idCliente = %s', (id_cliente,))
    if cursor.fetchone()['total_items'] == 0:
        flash('No hay artículos en el carrito para comprar', 'warning')
        return redirect(url_for('ver_carrito'))

    # 2. OBTENER DATOS DEL CLIENTE
    cursor.execute('SELECT Email, Nombre FROM Clientes WHERE idClientes = %s', (id_cliente,))
    cliente = cursor.fetchone()
    if not cliente:
        flash('Error al obtener datos del cliente', 'danger')
        return redirect(url_for('ver_carrito'))

    # 3. OBTENER PRODUCTOS CON PRECIO ACTUAL (IMPORTANTE)
    cursor.execute('''
        SELECT l.idLibro, l.Nombre, c.Cantidad, l.Precio 
        FROM Carrito c 
        JOIN Libro l ON c.idLibro = l.idLibro 
        WHERE c.idCliente = %s
    ''', (id_cliente,))
    libros = cursor.fetchall()

    # 4. CALCULAR TOTAL CORRECTO
    total = sum(libro['Cantidad'] * libro['Precio'] for libro in libros)

    # 5. REGISTRAR VENTAS Y ACTUALIZAR INVENTARIO
    try:
        for libro in libros:
            # Registrar venta
            cursor.execute('''
                INSERT INTO Ventas (Fecha, Monto, TipoPago, ID_libro, IDClientes)
                VALUES (NOW(), %s, 'Online', %s, %s)
            ''', (libro['Precio'] * libro['Cantidad'], libro['idLibro'], id_cliente))

            # Actualizar stock
            cursor.execute('''
                UPDATE Libro 
                SET Cantidad = Cantidad - %s,
                    Estado = CASE WHEN (Cantidad - %s) <= 0 THEN 'NoStock' ELSE 'Stock' END
                WHERE idLibro = %s
            ''', (libro['Cantidad'], libro['Cantidad'], libro['idLibro']))

        # 6. ENVIAR CORREO CON DATOS CORRECTOS
        mensaje = f"Gracias por tu compra, {cliente['Nombre']}!\n\nDetalles:\n"
        mensaje += "\n".join([
            f"- {libro['Nombre']} ({libro['Cantidad']} x ${libro['Precio']:.2f})"
            for libro in libros
        ])
        mensaje += f"\n\nTOTAL: ${total:.2f}"

        msg = Message(
            "Confirmación de compra",
            recipients=[cliente['Email']],
            body=mensaje
        )
        mail.send(msg)

        # 7. VACIAR CARRITO
        cursor.execute('DELETE FROM Carrito WHERE idCliente = %s', (id_cliente,))
        conn.commit()

        flash('Compra exitosa! Se envió la confirmación por correo', 'success')
        
    except Exception as e:
        conn.rollback()
        flash(f'Error al procesar la compra: {str(e)}', 'danger')
    finally:
        cursor.close()
        conn.close()

    return redirect(url_for('ver_carrito'))
if __name__ == '__main__':
    app.run(debug=True)