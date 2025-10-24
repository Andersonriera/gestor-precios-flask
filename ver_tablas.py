import sqlite3

conn = sqlite3.connect("productos.db")
cur = conn.cursor()

# Mostrar todas las tablas
print("Tablas en la base de datos:")
for row in cur.execute("SELECT name FROM sqlite_master WHERE type='table';"):
    print("-", row[0])

# Mostrar columnas de la tabla productos
print("\nColumnas en la tabla 'productos':")
for row in cur.execute("PRAGMA table_info(productos);"):
    print(row)

conn.close()
