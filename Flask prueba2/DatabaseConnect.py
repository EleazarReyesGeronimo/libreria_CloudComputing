from SQLAlchemy import MySQL

# Inicializar la extensión MySQL
mysql = MySQL()

def init_db(app):
    # Configuración de la base de datos MySQL
    app.config['MYSQL_HOST'] = '127.0.0.1:3306'  # o la IP de tu servidor MySQL
    app.config['MYSQL_USER'] = 'root'  # tu usuario de MySQL
    app.config['MYSQL_PASSWORD'] = 'root'  # tu contraseña de MySQL
    app.config['MYSQL_DB'] = 'mydb'  # nombre de la base de datos

    # Inicializar la conexión de MySQL con la app
    mysql.init_app(app)
