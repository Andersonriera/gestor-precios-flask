from flask import Flask, render_template, request, redirect
import psycopg2
from urllib.parse import urlparse
import os
from datetime import datetime

app = Flask(__name__)

# ------------------------------
# Conexión con PostgreSQL
# ------------------------------
def conectar():
    db_url = os.environ.get("DATABASE_URL")
    if not db_url:
        db_url = "postgresql://gestor_precios_db_user:moZxkQ8zyq7LeCHhFVchHmkJoK73FFzq@dpg-d3remkmmcj7s73cienkg-a/gestor_precios_db"

    result = urlparse(db_url)
    conn = psycopg2.connect(
        database=result.path[1:],
        user=result.username,
        password=result.password,
        host=result.hostname,
        port=result.port
    )
    return conn


# ------------------------------
# Crear tablas automáticamente
# ------------------------------
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
            print("✅ Tablas verificadas o creadas correctamente.")
    except Exception as e:
        print(⚠️ Error al crear tablas:", e)

crear_tablas()

# ------------------------------
# Página principal
# ------------------------------
@app.route('/')
def index():
    search = request.args.get('search', '')
    conn = conectar()
    cur = conn.cursor()

    if search:
        cur.execute("""
            SELECT p.*, 
                   MIN(pr.precio) AS precio_minimo, 
                   (SELECT proveedor FROM precios pr2 WHERE pr2.producto_id = p.id ORDER BY pr2.precio ASC LIMIT 1)
            FROM productos p
            LEFT JOIN precios pr ON p.id = pr.producto_id
            WHERE p.nombre ILIKE %s OR p.descripcion ILIKE %s
            GROUP BY p.id
        """, (f"%{search}%", f"%{search}%"))
    else:
        cur.execute("""
            SELECT p.*, 
                   MIN(pr.precio) AS precio_minimo, 
                   (SELECT proveedor FROM precios pr2 WHERE pr2.producto_id = p.id ORDER BY pr2.precio ASC LIMIT 1)
            FROM productos p
            LEFT JOIN precios pr ON p.id = pr.producto_id
            GROUP BY p.id
        """)

    productos = cur.fetchall()
    columnas = [desc[0] for desc in cur.description]
    productos = [dict(zip(columnas, fila)) for fila in productos]

    cur.close()
    conn.close()
    return render_template('index.html', productos=productos, search=search)


# ------------------------------
# Agregar producto
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


# ------------------------------
# Página de precios
# ------------------------------
@app.route('/precio/<int:producto_id>', methods=['GET', 'POST'])
def precio(producto_id):
    conn = conectar()
    cur = conn.cursor()

    if request.method == 'POST':
        proveedor = request.form['proveedor']
        precio_valor = float(request.form['precio'])
        fecha = datetime.now()
        cur.execute("""
            INSERT INTO precios (producto_id, proveedor, precio, fecha)
            VALUES (%s, %s, %s, %s)
        """, (producto_id, proveedor, precio_valor, fecha))
        conn.commit()

    cur.execute("SELECT * FROM productos WHERE id = %s", (producto_id,))
    producto = cur.fetchone()
    columnas = [desc[0] for desc in cur.description]
    producto = dict(zip(columnas, producto)) if producto else None

    cur.execute("""
        SELECT * FROM precios WHERE producto_id = %s ORDER BY fecha DESC
    """, (producto_id,))
    precios = cur.fetchall()
    columnas = [desc[0] for desc in cur.description]
    precios = [dict(zip(columnas, fila)) for fila in precios]

    precio_minimo = min(precios, key=lambda x: x['precio']) if precios else None

    cur.close()
    conn.close()

    return render_template('precios.html', producto=producto, precios=precios, precio_minimo=precio_minimo)


# ------------------------------
# Editar producto
# ------------------------------
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


# ------------------------------
# Eliminar producto
# ------------------------------
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


# ------------------------------
# Iniciar servidor
# ------------------------------
if __name__ == '__main__':
    app.run(debug=True)
