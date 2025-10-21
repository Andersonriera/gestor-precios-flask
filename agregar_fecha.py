import sqlite3

conn = sqlite3.connect('productos.db')
cursor = conn.cursor()

# Agregamos la columna 'fecha' solo si no existe
try:
    cursor.execute("ALTER TABLE precios ADD COLUMN fecha TEXT")
    print("✅ Columna 'fecha' agregada correctamente.")
except sqlite3.OperationalError:
    print("ℹ️ La columna 'fecha' ya existe.")

conn.commit()
conn.close()
