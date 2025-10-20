import sqlite3

# Crear o conectar a la base de datos
conexion = sqlite3.connect('productos.db')

# Crear un cursor para ejecutar comandos SQL
cursor = conexion.cursor()

# Crear tabla de productos
cursor.execute('''
CREATE TABLE IF NOT EXISTS productos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nombre TEXT NOT NULL,
    descripcion TEXT
)
''')

# Crear tabla de proveedores y precios
cursor.execute('''
CREATE TABLE IF NOT EXISTS precios (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    producto_id INTEGER,
    proveedor TEXT,
    precio REAL,
    FOREIGN KEY (producto_id) REFERENCES productos(id)
)
''')

conexion.commit()
conexion.close()

print("Base de datos creada correctamente ✅")
