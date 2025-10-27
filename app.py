from flask import Flask, render_template, request, redirect, url_for, make_response
import psycopg2
import psycopg2.extras
from datetime import datetime
import os

app = Flask(__name__)

# -----------------------------
# 🔹 Conexión a PostgreSQL
# -----------------------------
DATABASE_URL = os.environ.get("DATABASE_URL")

def conectar():
    conn = psycopg2.connect(DATABASE_URL, sslmode="require")
    return conn

# -----------------------------
# 🔹 Crear tablas automáticamente
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
    cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)

    if search:
        cur.execute("""
            SELECT * FROM productos 
            WHERE nombre ILIKE %s OR descripcion ILIKE %s 
            ORDER BY nombre ASC
        """, (f"%{search}%", f"%{search}%"))
    else:
        cur.execute("SELECT * FROM productos ORDER BY nombre ASC")

    productos = cur.fetchall()

    productos_con_precios = []
    for p in productos:
        cur.execute("SELECT MIN(precio) as mejor_precio FROM precios WHERE producto_id = %s", (p['id'],))
        resultado = cur.fetchone()
        mejor_precio = resultado['mejor_precio']

        precio_unitario = None
        if mejor_precio and p['unidades_por_caja']:
            precio_unitario = round(mejor_precio / p['unidades_por_caja'], 2)

        productos_con_precios.append({
            **dict(p),
            "mejor_precio": mejor_precio,
            "precio_unitario": precio_unitario
        })

    cur.close()
    conn.close()

    # 🔥 Forzar recarga de plantilla sin caché
    response = make_response(render_template("index.html", productos=productos_con_precios, search=search))
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    return response

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
            conn = None
            cur = None
            try:
                conn = conectar()
                cur = conn.cursor()
                cur.execute("""
                    INSERT INTO productos (nombre, descripcion, unidades_por_caja)
                    VALUES (%s, %s, %s)
                    RETURNING id;
                """, (nombre, descripcion, unidades_por_caja))
                
                # ✅ Obtener el ID del producto recién creado
                nuevo_id = cur.fetchone()[0]
                conn.commit()

                # ✅ Cerrar cursores y conexión correctamente
                cur.close()
                conn.close()

                # ✅ Redirigir directamente al detalle del nuevo producto
                return redirect(f'/detalle/{nuevo_id}')

            except psycopg2.IntegrityError:
                if conn:
                    conn.rollback()
                mensaje = "⚠️ El producto ya existe."
            except Exception as e:
                if conn:
                    conn.rollback()
                mensaje = f"❌ Error al guardar: {e}"
            finally:
                if cur:
                    cur.close()
                if conn:
                    conn.close()

    return render_template('agregar.html', mensaje=mensaje)

# -----------------------------
# 🔹 Editar producto
# -----------------------------
@app.route('/editar_producto/<int:id>', methods=['GET', 'POST'])
def editar_producto(id):
    conn = conectar()
    cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)

    cur.execute("SELECT * FROM productos WHERE id = %s", (id,))
    producto = cur.fetchone()
    if not producto:
        cur.close()
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
                    SET nombre = %s, descripcion = %s, unidades_por_caja = %s
                    WHERE id = %s
                """, (nombre, descripcion, unidades_por_caja, id))
                conn.commit()
                cur.close()
                conn.close()
                return redirect('/')
            except psycopg2.IntegrityError:
                mensaje = "⚠️ Nombre duplicado."
            except Exception as e:
                mensaje = f"❌ Error: {e}"

    cur.close()
    conn.close()
    return render_template('editar_producto.html', producto=producto, mensaje=mensaje)

@app.route('/eliminar/<int:id>')
def eliminar(id):
    try:
        conn = conectar()
        cur = conn.cursor()
        cur.execute("DELETE FROM productos WHERE id = %s", (id,))
        conn.commit()
        cur.close()
        conn.close()
        return redirect('/')
    except Exception as e:
        return f"❌ Error al eliminar: {e}"


# -----------------------------
# 🔹 Detalle del producto
# -----------------------------
@app.route('/detalle/<int:id>', methods=['GET', 'POST'])
def detalle(id):
    conn = conectar()
    cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)

    cur.execute("SELECT * FROM productos WHERE id = %s", (id,))
    producto = cur.fetchone()
    if not producto:
        cur.close()
        conn.close()
        return "Producto no encontrado", 404

    if request.method == 'POST':
        proveedor = request.form.get('proveedor')
        precio = request.form.get('precio', type=float)
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
        precio_minimo = min(precios, key=lambda x: x['precio'])
        unidades = producto['unidades_por_caja']
        if unidades and unidades > 0:
            precio_unitario = round(precio_minimo['precio'] / unidades, 2)

    cur.close()
    conn.close()
    return render_template('detalle.html', producto=producto, precios=precios,
                           precio_minimo=precio_minimo, precio_unitario=precio_unitario)

# -----------------------------
# 🔹 Iniciar servidor
# -----------------------------
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
