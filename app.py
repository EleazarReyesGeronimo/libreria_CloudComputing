from flask import Flask, render_template, request, redirect, url_for, flash, session
import mysql.connector
from datetime import datetime, timedelta

app = Flask(__name__)
app.secret_key = 'your_secret_key'  # Necesario para usar sesiones

# Configura tu conexión a la base de datos
def get_db_connection():
    conn = mysql.connector.connect(
        host='localhost',
        user='root',  # Cambia el usuario si es necesario
        password='root',  # Cambia la contraseña si es necesario
        database='Libreria'
    )
    return conn

# Página principal con los botones de inicio de sesión y crear cuenta
@app.route('/')
def home():
    return render_template('home.html')

# Página de inicio de sesión
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        usuario = request.form['usuario']
        contrasena = request.form['contrasena']

        # Conexión a la base de datos
        conn = get_db_connection()
        cursor = conn.cursor()

        # Verificar si el usuario existe en la tabla Administradores
        cursor.execute('SELECT * FROM Administradores WHERE Usuario = %s AND Contrasena = %s', (usuario, contrasena))
        user = cursor.fetchone()

        if user:
            session['usuario'] = usuario  # Guardamos el nombre de usuario en la sesión
            session['tipo_usuario'] = 'admin'  # Identificamos que es un administrador
            cursor.close()
            conn.close()
            return redirect(url_for('index'))  # Redirigir al área de libros o página principal

        else:
            flash('Credenciales incorrectas, por favor intenta nuevamente.', 'danger')
            cursor.close()
            conn.close()
            return redirect(url_for('login'))  # Vuelve al login si la autenticación falla

    return render_template('login.html')  # Página de login

# Página de inicio de sesión para clientes
@app.route('/login_cliente', methods=['GET', 'POST'])
def login_cliente():
    if request.method == 'POST':
        usuario = request.form['usuario']
        contrasena = request.form['contrasena']

        # Conexión a la base de datos
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)  # Usar dictionary=True para obtener resultados como diccionarios

        # Verificar si el usuario existe en la tabla Clientes
        cursor.execute('SELECT * FROM Clientes WHERE Usuario = %s AND Contrasena = %s', (usuario, contrasena))
        user = cursor.fetchone()

        if user:
            session['usuario'] = usuario  # Guardamos el nombre de usuario en la sesión
            session['id_cliente'] = user['idClientes']  # Guardamos el ID del cliente
            session['nombre_cliente'] = user['Nombre']  # Guardamos el nombre del cliente
            session['tipo_usuario'] = 'cliente'  # Identificamos que es un cliente
            cursor.close()
            conn.close()
            return redirect(url_for('catalogo'))  # Redirigir al catálogo de libros

        else:
            flash('Credenciales incorrectas, por favor intenta nuevamente.', 'danger')
            cursor.close()
            conn.close()
            return redirect(url_for('login_cliente'))  # Vuelve al login si la autenticación falla

    return render_template('login_cliente.html')  # Página de login para clientes

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

    return render_template('catalogo_cliente.html', libros=libros)


@app.route('/libro/<int:id>')
def detalle_libro(id):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM Libro WHERE idLibro = %s", (id,))
    libro = cursor.fetchone()
    cursor.close()
    conn.close()

    if not libro:
        flash("Libro no encontrado.", "danger")
        return redirect(url_for('catalogo'))

    return render_template('detalle_libro.html', libro=libro)


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
    
    cursor.close()
    conn.close()
    
    return render_template('perfil_cliente.html', cliente=cliente)

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
    
    # Datos de dirección
    calle = request.form['calle']
    colonia = request.form['colonia']
    cp = request.form['cp']
    num_exterior = request.form['num_exterior']
    num_interior = request.form['num_interior']
    num_contacto = request.form['num_contacto']
    
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    # Obtener el ID de la dirección del cliente
    cursor.execute('SELECT IDireccion FROM Clientes WHERE idClientes = %s', (session.get('id_cliente'),))
    id_direccion = cursor.fetchone()['IDireccion']
    
    # Actualizar la dirección
    cursor.execute('''
        UPDATE Direcciones 
        SET Calle = %s, Colonia = %s, CP = %s, NumExterior = %s, NumInterior = %s, NumContacto = %s 
        WHERE idDirecciones = %s
    ''', (calle, colonia, cp, num_exterior, num_interior, num_contacto, id_direccion))
    
    # Actualizar datos del cliente
    cursor.execute('''
        UPDATE Clientes 
        SET Nombre = %s, Apellidos = %s, Email = %s, Usuario = %s 
        WHERE idClientes = %s
    ''', (nombre, apellidos, email, usuario, session.get('id_cliente')))
    
    # Si se proporciona una nueva contraseña, actualizarla
    if 'contrasena' in request.form and request.form['contrasena'].strip():
        cursor.execute('UPDATE Clientes SET Contrasena = %s WHERE idClientes = %s', 
                      (request.form['contrasena'], session.get('id_cliente')))
    
    conn.commit()
    
    # Actualizar nombre de usuario en la sesión si cambió
    if session['usuario'] != usuario:
        session['usuario'] = usuario
        session['nombre_cliente'] = nombre
    
    cursor.close()
    conn.close()
    
    flash('Perfil actualizado exitosamente.', 'success')
    return redirect(url_for('perfil_cliente'))

# Página para gestionar los libros (CRUD)
@app.route('/index')
def index():
    if 'usuario' not in session:
        return redirect(url_for('login'))

    # Conexión a la base de datos
    conn = get_db_connection()
    cursor = conn.cursor()

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
    cantidad = request.form['cantidad']

    # Conexión a la base de datos
    conn = get_db_connection()
    cursor = conn.cursor()

    # Insertar el nuevo libro con fecha actual
    cursor.execute("""
        INSERT INTO Libro (Nombre, Editorial, Edicion, Estado, Cantidad, FechaCreacion)
        VALUES (%s, %s, %s, %s, %s, NOW())
    """, (nombre, editorial, edicion, estado, cantidad))

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
    cursor = conn.cursor()

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
    cursor = conn.cursor()

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

#Ruta para que el usuario pueda editar sus direcciones
@app.route('/gestion-direcciones', methods=['GET', 'POST'])
def gestion_direcciones():
    if 'usuario' not in session or session.get('tipo_usuario') != 'cliente':
        return redirect(url_for('login_cliente'))

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    if request.method == 'POST':
        accion = request.form.get('accion')

        if accion == 'agregar':
            # Agregar una nueva dirección
            calle = request.form['calle']
            colonia = request.form['colonia']
            cp = request.form['cp']
            num_exterior = request.form['num_exterior']
            num_interior = request.form['num_interior']
            num_contacto = request.form['num_contacto']

            cursor.execute("""
                INSERT INTO Direcciones (Calle, Colonia, CP, NumExterior, NumInterior, NumContacto, idCliente)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            """, (calle, colonia, cp, num_exterior, num_interior, num_contacto, session.get('id_cliente')))

            conn.commit()
            flash('Dirección agregada exitosamente.', 'success')

        elif accion == 'editar':
            # Editar una dirección existente
            direccion_id = request.form['direccion_id']
            calle = request.form['calle']
            colonia = request.form['colonia']
            cp = request.form['cp']
            num_exterior = request.form['num_exterior']
            num_interior = request.form['num_interior']
            num_contacto = request.form['num_contacto']

            cursor.execute("""
                UPDATE Direcciones 
                SET Calle = %s, Colonia = %s, CP = %s, NumExterior = %s, NumInterior = %s, NumContacto = %s
                WHERE idDirecciones = %s AND idCliente = %s
            """, (calle, colonia, cp, num_exterior, num_interior, num_contacto, direccion_id, session.get('id_cliente')))

            conn.commit()
            flash('Dirección actualizada exitosamente.', 'success')

        elif accion == 'eliminar':
            # Eliminar una dirección
            direccion_id = request.form['direccion_id']
            cursor.execute("""
                DELETE FROM Direcciones 
                WHERE idDirecciones = %s AND idCliente = %s
            """, (direccion_id, session.get('id_cliente')))
            conn.commit()
            flash('Dirección eliminada exitosamente.', 'success')

    # Obtener todas las direcciones del cliente
    cursor.execute("""
        SELECT * FROM Direcciones 
        WHERE idCliente = %s
    """, (session.get('id_cliente'),))
    direcciones = cursor.fetchall()

    cursor.close()
    conn.close()

    return render_template('gestion_direcciones.html', direcciones=direcciones)
if __name__ == '__main__':
    app.run(debug=True)