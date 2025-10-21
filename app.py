from flask import Flask, render_template, request, redirect
import psycopg2
import sqlite3
from urllib.parse import urlparse
import os
from datetime import datetime

app = Flask(__name__)

# ------------------------------
# 🔹 Conexión universal
# ------------------------------
def conectar():
    db_url = os.environ.get("DATABASE_URL")

    if db_url:  # Render (PostgreSQL)
        result = urlparse(db_url)
        conn = psycopg2.connect(
            database=result.path[1:],
            user=result.username,
            password=result.password,
            host=result.hostname,
            port=result.port
        )
        conn.tipo = "postgres"
        return conn
    else:  # Local (SQLite)
        conn = sqlite3.connect("productos.db")
        conn.tipo = "sqlite"
        return conn


# ------------------------------
# 🔹 Ejecutar SQL compatible (%s vs ?)
# ------------------------------
def ejecutar_sql(conn, query, params=()):
    cur = conn.cursor()
    if conn.tipo == "sqlite":
        query = query.replace("%s", "?")
    cur.execute(query, params)
    return cur


# ------------------------------
# 🔹 Crear tablas
# ------------------------------
def crear_tablas():
    try:
        conn = conectar()
        cur = conn.cursor()

        if conn.tipo == "postgres":
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
        else:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS productos (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    nombre TEXT,
                    descripcion TEXT,
                    precio_caja REAL,
                    unidades_por_caja INTEGER,
                    precio_unitario REAL
                )
            """)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS precios (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    producto_id INTEGER,
                    proveedor TEXT,
                    precio REAL,
                    fecha TEXT,
                    FOREIGN KEY (producto_id) REFERENCES productos(id)
                )
            """)

        conn.commit()
        cur.close()
        conn.close()
        print("✅ Tablas creadas/verificadas correctamente.")
    except Exception as e:
        print("❌ Error al crear tablas:", e)


crear_tablas()


# ------------------------------
# 🔹 Página principal (index)
# ------------------------------
@app.route('/')
def index():
    search = request.args.get('search', '')

    conn = conectar()
    cur = ejecutar_sql(conn, """
        SELECT 
            p.id,
            p.nombre,
            p.descripcion,
            p.unidades_por_caja,
            MIN(pr.precio) AS precio_minimo,
            (
                SELECT proveedor 
                FROM precios pr2 
                WHERE pr2.producto_id = p.id 
                ORDER BY pr2.precio ASC 
                LIMIT 1
            ) AS proveedor_minimo
        FROM productos p
        LEFT JOIN precios pr ON p.id = pr.producto_id
        WHERE p.nombre LIKE %s OR p.descripcion LIKE %s
        GROUP BY p.id
        ORDER BY p.nombre ASC
    """, (f"%{search}%", f"%{search}%"))

    productos = cur.fetchall()
    columnas = [desc[0] for desc in cur.description]
    productos = [dict(zip(columnas, fila)) for fila in productos]

    conn.close()
    return render_template('index.html', productos=productos, search=search)


# ------------------------------
# 🔹 Agregar producto
# ------------------------------
@app.route('/agregar', methods=['GET', 'POST'])
def agregar():
    if request.method == 'POST':
        nombre = request.form['nombre']
        descripcion = request.form['descripcion']
        precio_caja = float(request.form['precio_caja'])
        unidades_por_caja = int(request.form['unidades_por_caja'])
        precio_unitario = precio_caja / unidades_por_caja

        conn = conectar()
        ejecutar_sql(conn, """
            INSERT INTO productos (nombre, descripcion, precio_caja, unidades_por_caja, precio_unitario)
            VALUES (%s, %s, %s, %s, %s)
        """, (nombre, descripcion, precio_caja, unidades_por_caja, precio_unitario))
        conn.commit()
        conn.close()

        return redirect('/')
    return render_template('agregar.html')


# ------------------------------
# 🔹 Detalle del producto
# ------------------------------
@app.route('/detalle/<int:producto_id>', methods=['GET', 'POST'])
def detalle(producto_id):
    conn = conectar()

    if request.method == 'POST':
        proveedor = request.form['proveedor']
        precio_valor = float(request.form['precio'])
        fecha = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        ejecutar_sql(conn, """
            INSERT INTO precios (producto_id, proveedor, precio, fecha)
            VALUES (%s, %s, %s, %s)
        """, (producto_id, proveedor, precio_valor, fecha))
        conn.commit()

    cur = ejecutar_sql(conn, "SELECT * FROM productos WHERE id = %s", (producto_id,))
    producto = cur.fetchone()
    columnas = [desc[0] for desc in cur.description]
    producto = dict(zip(columnas, producto)) if producto else None

    cur = ejecutar_sql(conn, """
        SELECT proveedor, precio, fecha
        FROM precios
        WHERE producto_id = %s
        ORDER BY precio ASC
    """, (producto_id,))
    precios = cur.fetchall()
    columnas = [desc[0] for desc in cur.description]
    precios = [dict(zip(columnas, fila)) for fila in precios]

    precio_minimo = min(precios, key=lambda x: x['precio']) if precios else None

    conn.close()
    return render_template('detalle.html', producto=producto, precios=precios, precio_minimo=precio_minimo)


# ------------------------------
# 🔹 Editar producto
# ------------------------------
@app.route('/editar/<int:producto_id>', methods=['GET', 'POST'])
def editar(producto_id):
    conn = conectar()

    if request.method == 'POST':
        nombre = request.form['nombre']
        descripcion = request.form['descripcion']
        precio_caja = float(request.form['precio_caja'])
        unidades_por_caja = int(request.form['unidades_por_caja'])
        precio_unitario = precio_caja / unidades_por_caja

        ejecutar_sql(conn, """
            UPDATE productos
            SET nombre=%s, descripcion=%s, precio_caja=%s, unidades_por_caja=%s, precio_unitario=%s
            WHERE id=%s
        """, (nombre, descripcion, precio_caja, unidades_por_caja, precio_unitario, producto_id))
        conn.commit()
        conn.close()

        return redirect('/')

    cur = ejecutar_sql(conn, "SELECT * FROM productos WHERE id = %s", (producto_id,))
    producto = cur.fetchone()
    columnas = [desc[0] for desc in cur.description]
    producto = dict(zip(columnas, producto)) if producto else None

    conn.close()
    return render_template('editar.html', producto=producto)


# ------------------------------
# 🔹 Eliminar producto
# ------------------------------
@app.route('/eliminar/<int:producto_id>')
def eliminar(producto_id):
    conn = conectar()
    ejecutar_sql(conn, "DELETE FROM precios WHERE producto_id = %s", (producto_id,))
    ejecutar_sql(conn, "DELETE FROM productos WHERE id = %s", (producto_id,))
    conn.commit()
    conn.close()
    return redirect('/')


# ------------------------------
# 🔹 Iniciar servidor
# ------------------------------
if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)
