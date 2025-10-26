from flask import Flask, render_template, request, redirect, url_for
from datetime import datetime
import os
import psycopg2
import psycopg2.extras

app = Flask(__name__)

# -----------------------------
# 🔹 Conexión a la base de datos PostgreSQL
# -----------------------------
DATABASE_URL = os.environ.get("DATABASE_URL")  # ⚠️ Añádelo en Render → Environment

def conectar():
    conn = psycopg2.connect(DATABASE_URL, sslmode="require")
    return conn

# -----------------------------
# 🔹 Crear tablas automáticamente (si no existen)
# -----------------------------
def crear_tablas():
    conn = conectar()
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS productos (
            id SERIAL PRIMARY KEY,
            nombre TEXT UNIQUE,
            descripcion TEXT,
            unidades_por_caja INTEGER
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS precios (
            id SERIAL PRIMARY KEY,
            producto_id INTEGER REFERENCES productos(id) ON DELETE CASCADE,
            proveedor TEXT,
            precio REAL,
            fecha TEXT
        )
    """)
    conn.commit()
    cur.close()
    conn.close()

crear_tablas()

# -----------------------------
# 🔹 Página principal
# -----------------------------
@app.route("/")
def index():
    search = request.args.get("search", "")
    conn = conectar()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    if search:
        cur.execute("""
            SELECT * FROM productos
            WHERE nombre ILIKE %s OR descripcion ILIKE %s
            ORDER BY nombre ASC
        """, (f"%{search}%", f"%{search}%"))
    else:
        cur.execute("SELECT * FROM productos ORDER BY nombre ASC")

    productos = cur.fetchall()

    # Calcular mejor precio y precio unitario
    for p in productos:
        cur.execute("""
            SELECT proveedor, MIN(precio) AS mejor_precio
            FROM precios
            WHERE producto_id = %s
            GROUP BY proveedor
            ORDER BY mejor_precio ASC
            LIMIT 1
        """, (p["id"],))
        mejor = cur.fetchone()

        if mejor:
            p["mejor_precio"] = mejor["mejor_precio"]
            p["mejor_proveedor"] = mejor["proveedor"]
            p["precio_unitario"] = round(mejor["mejor_precio"] / p["unidades_por_caja"], 2) if p["unidades_por_caja"] else None
        else:
            p["mejor_precio"] = None
            p["mejor_proveedor"] = None
            p["precio_unitario"] = None

    cur.close()
    conn.close()
    return render_template("index.html", productos=productos, search=search)

# -----------------------------
# 🔹 Agregar producto
# -----------------------------
@app.route("/agregar", methods=["GET", "POST"])
def agregar():
    mensaje = None
    if request.method == "POST":
        nombre = request.form.get("nombre")
        descripcion = request.form.get("descripcion")
        unidades_por_caja = request.form.get("unidades_por_caja", type=int)

        if not nombre or not unidades_por_caja:
            mensaje = "⚠️ Faltan campos obligatorios."
        else:
            try:
                conn = conectar()
                cur = conn.cursor()
                cur.execute("""
                    INSERT INTO productos (nombre, descripcion, unidades_por_caja)
                    VALUES (%s, %s, %s)
                """, (nombre, descripcion, unidades_por_caja))
                conn.commit()
                cur.close()
                conn.close()
                return redirect("/")
            except psycopg2.errors.UniqueViolation:
                mensaje = "⚠️ El producto ya existe."
            except Exception as e:
                mensaje = f"❌ Error: {e}"

    return render_template("agregar.html", mensaje=mensaje)

# -----------------------------
# 🔹 Editar producto
# -----------------------------
@app.route("/editar_producto/<int:id>", methods=["GET", "POST"])
def editar_producto(id):
    conn = conectar()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute("SELECT * FROM productos WHERE id = %s", (id,))
    producto = cur.fetchone()

    if not producto:
        cur.close()
        conn.close()
        return "Producto no encontrado", 404

    mensaje = None
    if request.method == "POST":
        nombre = request.form.get("nombre")
        descripcion = request.form.get("descripcion")
        unidades_por_caja = request.form.get("unidades_por_caja", type=int)

        if not nombre or not unidades_por_caja:
            mensaje = "⚠️ Todos los campos son obligatorios."
        else:
            try:
                cur.execute("""
                    UPDATE productos
                    SET nombre = %s, descripcion = %s, unidades_por_caja = %s
                    WHERE id = %s
                """, (nombre, descripcion, unidades_por_caja, id))
                conn.commit()
                cur.close()
                conn.close()
                return redirect("/")
            except Exception as e:
                mensaje = f"❌ Error: {e}"

    cur.close()
    conn.close()
    return render_template("editar_producto.html", producto=producto, mensaje=mensaje)

# -----------------------------
# 🔹 Detalle del producto
# -----------------------------
@app.route("/detalle/<int:id>", methods=["GET", "POST"])
def detalle(id):
    conn = conectar()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    cur.execute("SELECT * FROM productos WHERE id = %s", (id,))
    producto = cur.fetchone()
    if not producto:
        cur.close()
        conn.close()
        return "Producto no encontrado", 404

    if request.method == "POST":
        proveedor = request.form.get("proveedor")
        precio = request.form.get("precio", type=float)
        if proveedor and precio is not None:
            cur.execute("""
                INSERT INTO precios (producto_id, proveedor, precio, fecha)
                VALUES (%s, %s, %s, %s)
            """, (id, proveedor, precio, datetime.now().strftime("%Y-%m-%d")))
            conn.commit()

    cur.execute("SELECT * FROM precios WHERE producto_id = %s ORDER BY precio ASC", (id,))
    precios = cur.fetchall()

    precio_minimo = None
    precio_unitario = None
    if precios:
        precio_minimo = min(precios, key=lambda x: x["precio"])
        unidades = producto["unidades_por_caja"]
        if unidades and unidades > 0:
            precio_unitario = round(precio_minimo["precio"] / unidades, 2)

    cur.close()
    conn.close()
    return render_template("detalle.html",
                           producto=producto,
                           precios=precios,
                           precio_minimo=precio_minimo,
                           precio_unitario=precio_unitario)

# -----------------------------
# 🔹 Editar precio de proveedor
# -----------------------------
@app.route("/editar_precio/<int:id>", methods=["GET", "POST"])
def editar_precio(id):
    conn = conectar()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute("SELECT * FROM precios WHERE id = %s", (id,))
    precio = cur.fetchone()

    if not precio:
        cur.close()
        conn.close()
        return "Precio no encontrado", 404

    cur.execute("SELECT * FROM productos WHERE id = %s", (precio["producto_id"],))
    producto = cur.fetchone()

    if request.method == "POST":
        nuevo_proveedor = request.form["proveedor"]
        nuevo_precio = request.form["precio"]
        cur.execute("""
            UPDATE precios SET proveedor = %s, precio = %s WHERE id = %s
        """, (nuevo_proveedor, nuevo_precio, id))
        conn.commit()
        cur.close()
        conn.close()
        return redirect(f"/detalle/{precio['producto_id']}")

    cur.close()
    conn.close()
    return render_template("editar_precio.html", precio=precio, producto=producto)

# -----------------------------
# 🔹 Eliminar producto o precio
# -----------------------------
@app.route("/eliminar/<int:producto_id>")
def eliminar(producto_id):
    conn = conectar()
    cur = conn.cursor()
    cur.execute("DELETE FROM precios WHERE producto_id = %s", (producto_id,))
    cur.execute("DELETE FROM productos WHERE id = %s", (producto_id,))
    conn.commit()
    cur.close()
    conn.close()
    return redirect(url_for("index"))

@app.route("/eliminar_precio/<int:precio_id>")
def eliminar_precio(precio_id):
    conn = conectar()
    cur = conn.cursor()
    cur.execute("DELETE FROM precios WHERE id = %s", (precio_id,))
    conn.commit()
    cur.close()
    conn.close()
    return redirect(request.referrer or "/")

# -----------------------------
# 🔹 Iniciar servidor
# -----------------------------
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)
