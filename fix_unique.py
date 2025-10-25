import sqlite3
import shutil
import os

# Ruta a tu base de datos
DB_PATH = "productos.db"
BACKUP_PATH = "productos_backup.db"

# Crear una copia de seguridad por seguridad
if os.path.exists(DB_PATH):
    shutil.copy(DB_PATH, BACKUP_PATH)
    print("✅ Copia de seguridad creada:", BACKUP_PATH)

# Conectar a la base existente
conn = sqlite3.connect(DB_PATH)
cur = conn.cursor()

# 1️⃣ Crear una tabla temporal con la restricción UNIQUE(nombre)
cur.execute("""
CREATE TABLE IF NOT EXISTS productos_temp (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nombre TEXT UNIQUE,
    descripcion TEXT,
    precio_caja REAL,
    unidades_por_caja INTEGER,
    precio_unitario REAL
)
""")

# 2️⃣ Copiar los datos actuales (ignorando duplicados)
try:
    cur.execute("""
        INSERT OR IGNORE INTO productos_temp (id, nombre, descripcion, precio_caja, unidades_por_caja, precio_unitario)
        SELECT id, nombre, descripcion, precio_caja, unidades_por_caja, precio_unitario FROM productos
    """)
    print("✅ Datos copiados a la tabla temporal (duplicados ignorados).")
except Exception as e:
    print("⚠️ Error al copiar los datos:", e)

# 3️⃣ Borrar la tabla vieja y renombrar la nueva
cur.execute("DROP TABLE productos")
cur.execute("ALTER TABLE productos_temp RENAME TO productos")

# Guardar cambios
conn.commit()
conn.close()
print("🎉 Tabla actualizada con UNIQUE(nombre). Ya no se podrán crear productos duplicados.")
