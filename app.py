from flask import Flask, render_template, request, redirect
import psycopg2
import os
# Crear tablas automáticamente en PostgreSQL si no existen
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
    print("⚠️ Error al crear tablas:", e)

from urllib.parse import urlparse

def conectar():
    db_url = os.environ.get("DATABASE_URL")
    if not db_url:
        # ⚠️ Pega tu URL de Render aquí (solo localmente, Render la usará como variable)
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
# Crear tablas si no existen
# ------------------------------
with conectar() as con:
    con.execute("""
        CREATE TABLE IF NOT EXISTS productos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre TEXT,
            descripcion TEXT,
            precio_caja REAL,
            unidades_por_caja INTEGER,
            precio_unitario REAL
        )
    """)
    con.execute("""
        CREATE TABLE IF NOT EXISTS precios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            producto_id INTEGER,
            proveedor TEXT,
            precio REAL,
            FOREIGN KEY (producto_id) REFERENCES productos(id)
        )
    """)

# ------------------------------
# Página principal
# ------------------------------
@app.route('/')
def index():
    search = request.args.get('search', '')

    conn = sqlite3.connect('productos.db')
    conn.row_factory = sqlite3.Row

    if search:
        productos = conn.execute("""
            SELECT p.*, 
                   MIN(pr.precio) AS precio_minimo, 
                   (SELECT proveedor FROM precios pr2 WHERE pr2.producto_id = p.id ORDER BY pr2.precio ASC LIMIT 1) AS proveedor_minimo
            FROM productos p
            LEFT JOIN precios pr ON p.id = pr.producto_id
            WHERE p.nombre LIKE ? OR p.descripcion LIKE ?
            GROUP BY p.id
        """, (f"%{search}%", f"%{search}%")).fetchall()
    else:
        productos = conn.execute("""
            SELECT p.*, 
                   MIN(pr.precio) AS precio_minimo, 
                   (SELECT proveedor FROM precios pr2 WHERE pr2.producto_id = p.id ORDER BY pr2.precio ASC LIMIT 1) AS proveedor_minimo
            FROM productos p
            LEFT JOIN precios pr ON p.id = pr.producto_id
            GROUP BY p.id
        """).fetchall()

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

        con = conectar()
        con.execute(
            "INSERT INTO productos (nombre, descripcion, precio_caja, unidades_por_caja, precio_unitario) VALUES (?, ?, ?, ?, ?)",
            (nombre, descripcion, precio_caja, unidades_por_caja, precio_unitario)
        )
        con.commit()
        con.close()
        return redirect('/')
    return render_template('agregar.html')

# ------------------------------
# Página de precios de proveedores
# ------------------------------
@app.route('/precio/<int:producto_id>', methods=['GET', 'POST'])
def precio(producto_id):
    from datetime import datetime
    con = conectar()
    producto = con.execute("SELECT * FROM productos WHERE id = ?", (producto_id,)).fetchone()

    if request.method == 'POST':
        proveedor = request.form['proveedor']
        precio_valor = request.form['precio']
        fecha = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        con.execute(
            'INSERT INTO precios (producto_id, proveedor, precio, fecha) VALUES (?, ?, ?, ?)',
            (producto_id, proveedor, precio_valor, fecha)
        )
        con.commit()

        return redirect(f'/precio/{producto_id}')

    # 🔹 Consultar todos los precios del producto
    precios = con.execute(
        'SELECT * FROM precios WHERE producto_id = ? ORDER BY fecha DESC',
        (producto_id,)
    ).fetchall()

    # 🔹 Calcular el precio más barato
    precio_minimo = None
    if precios:
        precio_minimo = min(precios, key=lambda x: x['precio'])

    con.close()

    # 🔹 Enviar todo a la plantilla HTML
    return render_template('precios.html', producto=producto, precios=precios, precio_minimo=precio_minimo)



# ------------------------------
# Editar producto
# ------------------------------
@app.route('/editar/<int:producto_id>', methods=['GET', 'POST'])
def editar(producto_id):
    con = conectar()
    producto = con.execute("SELECT * FROM productos WHERE id = ?", (producto_id,)).fetchone()

    if request.method == 'POST':
        nombre = request.form['nombre']
        descripcion = request.form['descripcion']
        precio_caja = float(request.form['precio_caja'])
        unidades_por_caja = int(request.form['unidades_por_caja'])
        precio_unitario = precio_caja / unidades_por_caja

        con.execute("""
            UPDATE productos 
            SET nombre=?, descripcion=?, precio_caja=?, unidades_por_caja=?, precio_unitario=?
            WHERE id=?
        """, (nombre, descripcion, precio_caja, unidades_por_caja, precio_unitario, producto_id))
        con.commit()
        con.close()
        return redirect('/')
    
    con.close()
    return render_template('editar.html', producto=producto)


# ------------------------------
# Eliminar producto
# ------------------------------
@app.route('/eliminar/<int:producto_id>')
def eliminar(producto_id):
    con = conectar()
    con.execute("DELETE FROM precios WHERE producto_id = ?", (producto_id,))
    con.execute("DELETE FROM productos WHERE id = ?", (producto_id,))
    con.commit()
    con.close()
    return redirect('/')
@app.route('/precio/<int:producto_id>', methods=['GET', 'POST'])
def agregar_precio(producto_id):
    conn = sqlite3.connect('productos.db')
    conn.row_factory = sqlite3.Row

    if request.method == 'POST':
        proveedor = request.form['proveedor']
        precio = request.form['precio']

        conn.execute(
            'INSERT INTO precios (producto_id, proveedor, precio, fecha) VALUES (?, ?, ?, DATE("now"))',
            (producto_id, proveedor, precio)
        )
        conn.commit()

    producto = conn.execute('SELECT * FROM productos WHERE id = ?', (producto_id,)).fetchone()
    precios = conn.execute(
        'SELECT proveedor, precio, fecha FROM precios WHERE producto_id = ? ORDER BY fecha DESC',
        (producto_id,)
    ).fetchall()

    conn.close()
    return render_template('precios.html', producto=producto, precios=precios)


# ------------------------------
# Iniciar servidor
# ------------------------------
if __name__ == '__main__':
    app.run(debug=True)
