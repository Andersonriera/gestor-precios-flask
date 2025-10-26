from flask import Flask, render_template, request, redirect, url_for
import sqlite3
from datetime import datetime
import os

app = Flask(__name__)

# -----------------------------
# 🔹 Conexión a la base de datos
# -----------------------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "productos.db")

def conectar():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

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
    cur = conn.cursor()

    # Buscar productos
    if search:
        cur.execute("""
            SELECT * FROM productos 
            WHERE nombre LIKE ? OR descripcion LIKE ? 
            ORDER BY nombre ASC
        """, (f"%{search}%", f"%{search}%"))
    else:
        cur.execute("SELECT * FROM productos ORDER BY nombre ASC")

    productos = cur.fetchall()

    # 🔹 Calcular el mejor precio y el precio unitario para cada producto
    productos_con_precios = []
    for p in productos:
        cur.execute("""
            SELECT MIN(precio) as mejor_precio
            FROM precios
            WHERE producto_id = ?
        """, (p['id'],))
        resultado = cur.fetchone()
        mejor_precio = resultado['mejor_precio']

        # Calcular precio unitario
        precio_unitario = None
        if mejor_precio and p['unidades_por_caja']:
            precio_unitario = round(mejor_precio / p['unidades_por_caja'], 2)

        productos_con_precios.append({
            **dict(p),
            "mejor_precio": mejor_precio,
            "precio_unitario": precio_unitario
        })

    conn.close()
    return render_template("index.html", productos=productos_con_precios, search=search)

# -----------------------------
# 🔹 Agregar producto
# -----------------------------
@app.route('/agregar', methods=['GET', 'POST'])
def agregar():
    mensaje = None
    if request.method == 'POST':
        nombre = request.form.get('nombre')
        descripcion = request.form.get('descripcion')
        unidades_por_caja = request.form.get('unidades_por_caja', type=int)

        if not nombre or not unidades_por_caja:
            mensaje = "⚠️ Faltan campos obligatorios."
        else:
            try:
                conn = conectar()
                cur = conn.cursor()
                cur.execute("""
                    INSERT INTO productos (nombre, descripcion, unidades_por_caja)
                    VALUES (?, ?, ?)
                """, (nombre, descripcion, unidades_por_caja))
                conn.commit()
                conn.close()
                return redirect('/')
            except sqlite3.IntegrityError:
                mensaje = "⚠️ El producto ya existe. Intenta con otro nombre."
            except Exception as e:
                mensaje = f"❌ Error al agregar producto: {e}"

    return render_template('agregar.html', mensaje=mensaje)

# -----------------------------
# 🔹 Editar producto
# -----------------------------
@app.route('/editar_producto/<int:id>', methods=['GET', 'POST'])
def editar_producto(id):
    conn = conectar()
    cur = conn.cursor()

    cur.execute("SELECT * FROM productos WHERE id = ?", (id,))
    producto = cur.fetchone()

    if not producto:
        conn.close()
        return "Producto no encontrado", 404

    mensaje = None
    if request.method == 'POST':
        nombre = request.form.get('nombre')
        descripcion = request.form.get('descripcion')
        unidades_por_caja = request.form.get('unidades_por_caja', type=int)

        if not nombre or not unidades_por_caja:
            mensaje = "⚠️ Todos los campos son obligatorios."
        else:
            try:
                cur.execute("""
                    UPDATE productos
                    SET nombre = ?, descripcion = ?, unidades_por_caja = ?
                    WHERE id = ?
                """, (nombre, descripcion, unidades_por_caja, id))
                conn.commit()
                conn.close()
                return redirect('/')
            except sqlite3.IntegrityError:
                mensaje = "⚠️ Ya existe un producto con ese nombre."
            except Exception as e:
                mensaje = f"❌ Error al actualizar: {e}"

    conn.close()
    return render_template('editar_producto.html', producto=producto, mensaje=mensaje)

# -----------------------------
# 🔹 Detalle del producto
# -----------------------------
@app.route('/detalle/<int:id>', methods=['GET', 'POST'])
def detalle(id):
    conn = conectar()
    cur = conn.cursor()

    cur.execute("SELECT * FROM productos WHERE id = ?", (id,))
    producto = cur.fetchone()
    if not producto:
        conn.close()
        return "Producto no encontrado", 404

    # Agregar nuevo precio
    if request.method == 'POST':
        proveedor = request.form.get('proveedor')
        precio = request.form.get('precio', type=float)
        if proveedor and precio is not None:
            cur.execute("""
                INSERT INTO precios (producto_id, proveedor, precio, fecha)
                VALUES (?, ?, ?, ?)
            """, (id, proveedor, precio, datetime.now().strftime("%Y-%m-%d")))
            conn.commit()

    # Obtener precios
    cur.execute("SELECT * FROM precios WHERE producto_id = ? ORDER BY precio ASC", (id,))
    precios = cur.fetchall()

    # Calcular precio mínimo y unitario
    precio_minimo = None
    precio_unitario = None
    if precios:
        precio_minimo = min(precios, key=lambda x: x['precio'])
        unidades = producto['unidades_por_caja']
        if unidades and unidades > 0:
            precio_unitario = round(precio_minimo['precio'] / unidades, 2)

    conn.close()
    return render_template(
        'detalle.html',
        producto=producto,
        precios=precios,
        precio_minimo=precio_minimo,
        precio_unitario=precio_unitario
    )

# -----------------------------
# 🔹 Editar precio de proveedor
# -----------------------------
@app.route("/editar_precio/<int:id>", methods=["GET", "POST"])
def editar_precio(id):
    conn = conectar()
    cur = conn.cursor()

    cur.execute("SELECT * FROM precios WHERE id = ?", (id,))
    precio = cur.fetchone()
    if not precio:
        conn.close()
        return "Precio no encontrado", 404

    cur.execute("SELECT * FROM productos WHERE id = ?", (precio['producto_id'],))
    producto = cur.fetchone()

    if request.method == "POST":
        nuevo_proveedor = request.form['proveedor']
        nuevo_precio = request.form['precio']
        cur.execute("""
            UPDATE precios
            SET proveedor = ?, precio = ?
            WHERE id = ?
        """, (nuevo_proveedor, nuevo_precio, id))
        conn.commit()
        conn.close()
        return redirect(f"/detalle/{precio['producto_id']}")

    conn.close()
    return render_template("editar_precio.html", precio=precio, producto=producto)

# -----------------------------
# 🔹 Eliminar producto y precios
# -----------------------------
@app.route("/eliminar/<int:producto_id>")
def eliminar(producto_id):
    conn = conectar()
    cur = conn.cursor()
    cur.execute("DELETE FROM precios WHERE producto_id = ?", (producto_id,))
    cur.execute("DELETE FROM productos WHERE id = ?", (producto_id,))
    conn.commit()
    conn.close()
    return redirect(url_for("index"))

# -----------------------------
# 🔹 Eliminar precio individual
# -----------------------------
@app.route("/eliminar_precio/<int:precio_id>")
def eliminar_precio(precio_id):
    conn = conectar()
    cur = conn.cursor()
    cur.execute("DELETE FROM precios WHERE id = ?", (precio_id,))
    conn.commit()
    conn.close()
    return redirect(request.referrer or "/")

# -----------------------------
# 🔹 Iniciar servidor
# -----------------------------
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)
