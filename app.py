from flask import Flask, render_template, request, redirect, url_for, flash, session
import mysql.connector

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
            cursor.close()
            conn.close()
            return redirect(url_for('index'))  # Redirigir al área de libros o página principal

        else:
            # Verificar en la tabla Clientes si la contraseña es correcta
            cursor.execute('SELECT * FROM Administradores WHERE Usuario = %s AND Contrasena = %s', (usuario, contrasena))
            user = cursor.fetchone()

            if user:
                session['usuario'] = usuario  # Guardamos el nombre de usuario en la sesión
                cursor.close()
                conn.close()
                return redirect(url_for('index'))  # Redirigir al área de libros o página principal

            else:
                flash('Credenciales incorrectas, por favor intenta nuevamente.')
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
        cursor = conn.cursor()

        # Verificar si el usuario existe en la tabla Clientes
        cursor.execute('SELECT * FROM Clientes WHERE Usuario = %s AND Contrasena = %s', (usuario, contrasena))
        user = cursor.fetchone()

        if user:
            session['usuario'] = usuario  # Guardamos el nombre de usuario en la sesión
            cursor.close()
            conn.close()
            return redirect(url_for('index'))  # Redirigir al área de libros o página principal

        else:
            flash('Credenciales incorrectas, por favor intenta nuevamente.')
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

    flash('Cuenta creada exitosamente, ya puedes iniciar sesión.')
    return redirect(url_for('home'))

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
    if 'usuario' not in session:
        return redirect(url_for('login'))

    nombre = request.form['nombre']
    editorial = request.form['editorial']
    edicion = request.form['edicion']
    estado = request.form['estado']
    cantidad = request.form['cantidad']

    # Conexión a la base de datos
    conn = get_db_connection()
    cursor = conn.cursor()

    # Insertar el nuevo libro
    cursor.execute("""
        INSERT INTO Libro (Nombre, Editorial, Edicion, Estado, Cantidad)
        VALUES (%s, %s, %s, %s, %s)
    """, (nombre, editorial, edicion, estado, cantidad))

    conn.commit()
    cursor.close()
    conn.close()

    flash('Libro agregado exitosamente.')
    return redirect(url_for('index'))

# Ruta para editar un libro
@app.route('/editar-libro/<int:id>', methods=['GET', 'POST'])
def editar_libro(id):
    if 'usuario' not in session:
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

        flash('Libro actualizado exitosamente.')
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
    if 'usuario' not in session:
        return redirect(url_for('login'))

    conn = get_db_connection()
    cursor = conn.cursor()

    # Eliminar el libro
    cursor.execute('DELETE FROM Libro WHERE idLibro = %s', (id,))
    conn.commit()

    cursor.close()
    conn.close()

    flash('Libro eliminado exitosamente.')
    return redirect(url_for('index'))

# Ruta para cerrar sesión
@app.route('/logout')
def logout():
    session.pop('usuario', None)
    flash('Has cerrado sesión exitosamente.')
    return redirect(url_for('home'))

if __name__ == '__main__':
    app.run(debug=True)
