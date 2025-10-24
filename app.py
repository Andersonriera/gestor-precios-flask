from flask import Flask, render_template, request, redirect, url_for
import sqlite3
from datetime import datetime
import os

app = Flask(__name__)

# -----------------------------
# 🔹 Conexión a la base de datos
# -----------------------------
def conectar():
    conn = sqlite3.connect("productos.db")
    conn.row_factory = sqlite3.Row
    return conn

def ejecutar_sql(conn, query, params=(), fetch=False):
    cur = conn.cursor()
    cur.execute(query, params)
    if fetch:
        return cur.fetchall()
    conn.commit()
    return None

# -----------------------------
# 🔹 Crear tablas automáticamente
# -----------------------------
def crear_tablas():
    conn = conectar()
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS productos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre TEXT UNIQUE,
            descripcion TEXT,
            unidades_por_caja INTEGER
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

crear_tablas()

# -----------------------------
# 🔹 Página principal
# -----------------------------
@app.route("/")
def index():
    search = request.args.get("search", "")
    conn = conectar()

    if search:
        productos = ejecutar_sql(conn, 
            "SELECT * FROM productos WHERE nombre LIKE ? OR descripcion LIKE ? ORDER BY nombre ASC", 
            (f"%{search}%", f"%{search}%"), 
            fetch=True
        )
    else:
        productos = ejecutar_sql(conn, "SELECT * FROM productos ORDER BY nombre ASC", fetch=True)

    conn.close()
    return render_template("index.html", productos=productos, search=search)

@app.route("/eliminar_producto/<int:id>", methods=["POST"])
def eliminar_producto(id):
    conn = conectar()
    cur = conn.cursor()

    # Primero eliminamos los precios asociados al producto (si los hay)
    cur.execute("DELETE FROM precios WHERE producto_id = ?", (id,))
    # Luego eliminamos el producto
    cur.execute("DELETE FROM productos WHERE id = ?", (id,))

    conn.commit()
    conn.close()
    return ("", 204)  # Respuesta vacía pero con código HTTP 204 (éxito sin contenido)


# -----------------------------
# 🔹 Agregar producto
# -----------------------------
@app.route("/agregar", methods=["GET", "POST"])
def agregar():
    if request.method == "POST":
        nombre = request.form.get("nombre")
        descripcion = request.form.get("descripcion")
        unidades_por_caja = request.form.get("unidades_por_caja", type=int)

        if not nombre or not unidades_por_caja:
            return "⚠️ Faltan campos obligatorios", 400

        conn = conectar()
        try:
            ejecutar_sql(conn, """
                INSERT INTO productos (nombre, descripcion, unidades_por_caja)
                VALUES (?, ?, ?)
            """, (nombre, descripcion, unidades_por_caja))
        except sqlite3.IntegrityError:
            conn.close()
            return "❌ Ya existe un producto con ese nombre.", 400

        conn.close()
        return redirect(url_for("index"))
    
    return render_template("agregar.html")

# -----------------------------
# 🔹 Detalle del producto
# -----------------------------
@app.route('/detalle/<int:id>', methods=['GET', 'POST'])
def detalle(id):
    conn = conectar()
    cur = conn.cursor()

    # Obtener el producto
    cur.execute("SELECT * FROM productos WHERE id = ?", (id,))
    producto = cur.fetchone()

    # Manejar POST: agregar nuevo precio
    if request.method == 'POST':
        proveedor = request.form.get('proveedor')
        precio = request.form.get('precio', type=float)

        if proveedor and precio is not None:
            cur.execute("""
                INSERT INTO precios (producto_id, proveedor, precio, fecha)
                VALUES (?, ?, ?, DATE('now'))
            """, (id, proveedor, precio))
            conn.commit()

    # Obtener precios asociados al producto
    cur.execute("SELECT * FROM precios WHERE producto_id = ? ORDER BY precio ASC", (id,))
    precios = cur.fetchall()

    # Encontrar el precio mínimo (si hay)
    precio_minimo = None
    if precios:
        precio_minimo = min(precios, key=lambda x: x['precio'])

    conn.close()

    return render_template('detalle.html', producto=producto, precios=precios, precio_minimo=precio_minimo)
# -----------------------------
# 🔹 Editar precio del proveedor
# -----------------------------
@app.route('/editar_precio/<int:id>', methods=['GET', 'POST'])
def editar_precio(id):
    conn = conectar()
    cur = conn.cursor()

    if request.method == 'POST':
        nuevo_precio = request.form.get('precio', type=float)

        # Buscar el producto al que pertenece este precio
        cur.execute("SELECT producto_id FROM precios WHERE id = ?", (id,))
        producto = cur.fetchone()
        if not producto:
            conn.close()
            return "Precio no encontrado", 404

        producto_id = producto['producto_id']

        # Actualizar el precio
        cur.execute("UPDATE precios SET precio = ? WHERE id = ?", (nuevo_precio, id))
        conn.commit()
        conn.close()

        # Redirigir al detalle del producto
        return redirect(f'/detalle/{producto_id}')

    # GET → Mostrar el formulario
    cur.execute("SELECT * FROM precios WHERE id = ?", (id,))
    precio = cur.fetchone()
    conn.close()
    return render_template('editar_precio.html', precio=precio)

# -----------------------------
# 🔹 Eliminar producto
# -----------------------------
@app.route("/eliminar/<int:producto_id>")
def eliminar(producto_id):
    conn = conectar()
    ejecutar_sql(conn, "DELETE FROM precios WHERE producto_id = ?", (producto_id,))
    ejecutar_sql(conn, "DELETE FROM productos WHERE id = ?", (producto_id,))
    conn.close()
    return redirect(url_for("index"))

# -----------------------------
# 🔹 Eliminar precio individual
# -----------------------------
@app.route("/eliminar_precio/<int:precio_id>")
def eliminar_precio(precio_id):
    conn = conectar()
    ejecutar_sql(conn, "DELETE FROM precios WHERE id = ?", (precio_id,))
    conn.close()
    return redirect(request.referrer or "/")

# -----------------------------
# 🔹 Iniciar servidor
# -----------------------------
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)
