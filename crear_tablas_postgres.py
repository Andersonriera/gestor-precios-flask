from app import conectar

conn = conectar()
cur = conn.cursor()

cur.execute("""
CREATE TABLE IF NOT EXISTS productos (
    id SERIAL PRIMARY KEY,
    nombre TEXT,
    descripcion TEXT,
    precio_caja REAL,
    unidades_por_caja INTEGER,
    precio_unitario REAL
)
""")

cur.execute("""
CREATE TABLE IF NOT EXISTS precios (
    id SERIAL PRIMARY KEY,
    producto_id INTEGER REFERENCES productos(id),
    proveedor TEXT,
    precio REAL,
    fecha TIMESTAMP
)
""")

conn.commit()
cur.close()
conn.close()

print("✅ Tablas creadas correctamente en PostgreSQL")
