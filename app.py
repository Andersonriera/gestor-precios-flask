from flask import Flask, render_template, request, redirect
import psycopg2
from urllib.parse import urlparse
import os
from datetime import datetime
import sqlite3

app = Flask(__name__)

# --------------------------------
# 🔹 Conexión automática (PostgreSQL en Render / SQLite local)
# --------------------------------
def conectar():
    db_url = os.environ.get("DATABASE_URL")

    if db_url:  # Render → PostgreSQL
        result = urlparse(db_url)
        conn = psycopg2.connect(
            database=result.path[1:],
            user=result.username,
            password=result.password,
            host=result.hostname,
            port=result.port
        )
        return conn
    else:  # Local → SQLite
        return sqlite3.connect("productos.db")

# --------------------------------
# 🔹 Crear tablas automáticamente
# --------------------------------
def crear_tablas():
    try:
        with conectar() as conn:
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
            print("✅ Tablas creadas o verificadas correctamente.")
    except Exception as e:
        print("⚠️ Error al crear tablas:", e)

crear_tablas()

# --------------------------------
# 🏠 Página principal
# --------------------------------
@app.route('/')
def index():
    search = request.args.get('search', '')

    conn = conectar()
    cur = conn.cursor()

    if search:
        cur.execute("""
            SELECT id, nombre, descripcion, unidades_por_caja
            FROM productos
            WHERE nombre ILIKE %s OR descripcion ILIKE %s
            ORDER BY nombre ASC
        """, (f"%{search}%", f"%{search}%"))
    else:
        cur.execute("""
            SELECT id, nombre, descripcion, unidades_por_caja
            FROM productos
            ORDER BY nombre ASC
        """)

    productos = cur.fetchall()
    columnas = [desc[0] for desc in cur.description]
    productos = [dict(zip(columnas, fila)) for fila in productos]

    cur.close()
    conn.close()

    return render_template('index.html', productos=productos, search=search)

# --------------------------------
# ➕ Agregar producto
# --------------------------------
@app.route('/agregar', methods=['GET', 'POST'])
def agregar():
    if request.method == 'POST':
        nombre = request.form['nombre']
        descripcion = request.form['descripcion']
        precio_caja = float(request.form['precio_caja'])
        unidades_por_caja = int(request.form['unidades_por_caja'])
        precio_unitario = precio_caja / unidades_por_caja

        conn = conectar()
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO productos (nombre, descripcion, precio_caja, unidades_por_caja, precio_unitario)
            VALUES (%s, %s, %s, %s, %s)
        """, (nombre, descripcion, precio_caja, unidades_por_caja, precio_unitario))
        conn.commit()
        cur.close()
        conn.close()
        return redirect('/')
    return render_template('agregar.html')

# --------------------------------
# 🔍 Detalle del producto (ver precios y proveedor más barato)
# --------------------------------
@app.route('/detalle/<int:producto_id>', methods=['GET', 'POST'])
def detalle(producto_id):
    conn = conectar()
    cur = conn.cursor()

    # Detectar si usamos SQLite o PostgreSQL
    is_sqlite = "sqlite" in str(type(conn)).lower()
    placeholder = "?" if is_sqlite else "%s"

    # Obtener producto
    cur.execute(f"SELECT * FROM productos WHERE id = {placeholder}", (producto_id,))
    producto = cur.fetchone()

    if not producto:
        conn.close()
        return "Producto no encontrado", 404

    columnas = [desc[0] for desc in cur.description]
    producto = dict(zip(columnas, producto))

    # Agregar nuevo precio si se envía formulario
    if request.method == 'POST':
        proveedor = request.form['proveedor']
        precio_valor = float(request.form['precio'])
        fecha = datetime.now()

        cur.execute(
            f"INSERT INTO precios (producto_id, proveedor, precio, fecha) VALUES ({placeholder}, {placeholder}, {placeholder}, {placeholder})",
            (producto_id, proveedor, precio_valor, fecha)
        )
        conn.commit()

    # Consultar precios existentes
    cur.execute(
        f"SELECT proveedor, precio, fecha FROM precios WHERE producto_id = {placeholder} ORDER BY precio ASC",
        (producto_id,)
    )
    precios = cur.fetchall()
    columnas = [desc[0] for desc in cur.description]
    precios = [dict(zip(columnas, fila)) for fila in precios]

    precio_minimo = min(precios, key=lambda x: x['precio']) if precios else None

    conn.close()

    return render_template('detalle.html', producto=producto, precios=precios, precio_minimo=precio_minimo)
# --------------------------------
# ✏️ Editar producto
# --------------------------------
@app.route('/editar/<int:producto_id>', methods=['GET', 'POST'])
def editar(producto_id):
    conn = conectar()
    cur = conn.cursor()

    if request.method == 'POST':
        nombre = request.form['nombre']
        descripcion = request.form['descripcion']
        precio_caja = float(request.form['precio_caja'])
        unidades_por_caja = int(request.form['unidades_por_caja'])
        precio_unitario = precio_caja / unidades_por_caja

        cur.execute("""
            UPDATE productos
            SET nombre=%s, descripcion=%s, precio_caja=%s, unidades_por_caja=%s, precio_unitario=%s
            WHERE id=%s
        """, (nombre, descripcion, precio_caja, unidades_por_caja, precio_unitario, producto_id))
        conn.commit()
        cur.close()
        conn.close()
        return redirect('/')

    cur.execute("SELECT * FROM productos WHERE id = %s", (producto_id,))
    producto = cur.fetchone()
    columnas = [desc[0] for desc in cur.description]
    producto = dict(zip(columnas, producto)) if producto else None

    cur.close()
    conn.close()
    return render_template('editar.html', producto=producto)

# --------------------------------
# 🗑️ Eliminar producto
# --------------------------------
@app.route('/eliminar/<int:producto_id>')
def eliminar(producto_id):
    conn = conectar()
    cur = conn.cursor()
    cur.execute("DELETE FROM precios WHERE producto_id = %s", (producto_id,))
    cur.execute("DELETE FROM productos WHERE id = %s", (producto_id,))
    conn.commit()
    cur.close()
    conn.close()
    return redirect('/')

# --------------------------------
# 🚀 Iniciar servidor
# --------------------------------
if __name__ == '__main__':
    app.run(debug=True)
