import mysql.connector

db_config = {
    "host": "localhost",
    "user": "root",
    "password": "root",
    "database": "Libreria"
}

def get_db_connection():
    return mysql.connector.connect(**db_config)
