from flask import Flask, render_template, request, redirect
import psycopg2
from urllib.parse import urlparse
import sqlite3
import os
from datetime import datetime

app = Flask(__name__)

# ------------------------------
# 🔹 Conexión a base de datos (SQLite local / PostgreSQL en Render)
# ------------------------------
def conectar():
    db_url = os.environ.get("DATABASE_URL")
    if db_url:
        result = urlparse(db_url)
        conn = psycopg2.connect(
            database=result.path[1:],
            user=result.username,
            password=result.password,
            host=result.hostname,
            port=result.port
        )
    else:
        conn = sqlite3.connect("productos.db")
    return conn


# ------------------------------
# 🔹 Función universal para ejecutar SQL
# ------------------------------
def ejecutar_sql(conn, query, params=(), fetch=False):
    cur = conn.cursor()
    driver = conn.__class__.__module__

    # Si es SQLite, reemplazar %s por ?
    if "sqlite3" in driver:
        query = query.replace("%s", "?")

    cur.execute(query, params)

    data = None
    if fetch:
        data = cur.fetchall()
        columnas = [desc[0] for desc in cur.description] if cur.description else []
        data = [dict(zip(columnas, fila)) for fila in data]

    cur.close()
    return data


# ------------------------------
# 🔹 Crear tablas automáticamente
# ------------------------------
def crear_tablas():
    conn = conectar()
    cur = conn.cursor()

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
    conn.close()

# Llamar a la función apenas inicia la app
crear_tablas()


# ------------------------------
# 🔹 Página principal
# ------------------------------
@app.route("/")
def index():
    conn = conectar()
    productos = ejecutar_sql(conn, "SELECT * FROM productos", fetch=True)
    conn.close()
    return render_template("index.html", productos=productos)


# ------------------------------
# 🔹 Agregar producto
# ------------------------------
@app.route("/agregar", methods=["GET", "POST"])
def agregar():
    if request.method == "POST":
        nombre = request.form.get("nombre")
        descripcion = request.form.get("descripcion")
        precio_caja = request.form.get("precio_caja", type=float)
        unidades_por_caja = request.form.get("unidades_por_caja", type=int)

        if not nombre or not precio_caja or not unidades_por_caja:
            return "Faltan campos obligatorios", 400

        precio_unitario = precio_caja / unidades_por_caja

        conn = conectar()
        ejecutar_sql(conn, """
            INSERT INTO productos (nombre, descripcion, precio_caja, unidades_por_caja, precio_unitario)
            VALUES (%s, %s, %s, %s, %s)
        """, (nombre, descripcion, precio_caja, unidades_por_caja, precio_unitario))
        conn.commit()
        conn.close()
        return redirect("/")

    return render_template("agregar.html")


# ------------------------------
# 🔹 Detalle del producto
# ------------------------------
@app.route("/detalle/<int:producto_id>", methods=["GET", "POST"])
def detalle(producto_id):
    conn = conectar()

    if request.method == "POST":
        proveedor = request.form.get("proveedor")
        precio = request.form.get("precio", type=float)
        fecha = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        ejecutar_sql(conn, """
            INSERT INTO precios (producto_id, proveedor, precio, fecha)
            VALUES (%s, %s, %s, %s)
        """, (producto_id, proveedor, precio, fecha))
        conn.commit()

    producto = ejecutar_sql(conn, "SELECT * FROM productos WHERE id = %s", (producto_id,), fetch=True)
    precios = ejecutar_sql(conn, "SELECT * FROM precios WHERE producto_id = %s ORDER BY precio ASC", (producto_id,), fetch=True)
    conn.close()

    producto = producto[0] if producto else None
    precio_minimo = min(precios, key=lambda x: x["precio"]) if precios else None

    return render_template("detalle.html", producto=producto, precios=precios, precio_minimo=precio_minimo)


# ------------------------------
# 🔹 Editar producto
# ------------------------------
@app.route("/editar/<int:id>", methods=["GET", "POST"])
def editar(id):
    conn = conectar()

    if request.method == "POST":
        nombre = request.form.get("nombre")
        descripcion = request.form.get("descripcion")
        precio_caja = request.form.get("precio_caja", type=float)
        unidades_por_caja = request.form.get("unidades_por_caja", type=int)
        precio_unitario = precio_caja / unidades_por_caja

        ejecutar_sql(conn, """
            UPDATE productos SET nombre=%s, descripcion=%s, precio_caja=%s, unidades_por_caja=%s, precio_unitario=%s
            WHERE id=%s
        """, (nombre, descripcion, precio_caja, unidades_por_caja, precio_unitario, id))
        conn.commit()
        conn.close()
        return redirect("/")

    producto = ejecutar_sql(conn, "SELECT * FROM productos WHERE id = %s", (id,), fetch=True)
    conn.close()
    producto = producto[0] if producto else None

    return render_template("editar.html", producto=producto)


# ------------------------------
# 🔹 Eliminar producto
# ------------------------------
@app.route("/eliminar/<int:id>")
def eliminar(id):
    conn = conectar()
    ejecutar_sql(conn, "DELETE FROM precios WHERE producto_id = %s", (id,))
    ejecutar_sql(conn, "DELETE FROM productos WHERE id = %s", (id,))
    conn.commit()
    conn.close()
    return redirect("/")


# ------------------------------
# 🔹 Iniciar servidor
# ------------------------------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)), debug=True)
