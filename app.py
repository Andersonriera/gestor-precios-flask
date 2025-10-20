from flask import Flask, render_template, request, redirect
import sqlite3

app = Flask(__name__)

# ------------------------------
# Función para conectar a la base
# ------------------------------
def conectar():
    conexion = sqlite3.connect('productos.db')
    conexion.row_factory = sqlite3.Row
    return conexion

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
    conn = sqlite3.connect('productos.db')
    conn.row_factory = sqlite3.Row
    productos = conn.execute('SELECT * FROM productos').fetchall()
    conn.close()

    return render_template('index.html', productos=productos)
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
    con = conectar()
    producto = con.execute("SELECT * FROM productos WHERE id = ?", (producto_id,)).fetchone()

    if request.method == 'POST':
        proveedor = request.form['proveedor']
        precio = float(request.form['precio'])
        con.execute("INSERT INTO precios (producto_id, proveedor, precio) VALUES (?, ?, ?)", (producto_id, proveedor, precio))
        con.commit()

    # Ordenar los precios de menor a mayor
    precios = con.execute(
        "SELECT * FROM precios WHERE producto_id = ? ORDER BY precio ASC",
        (producto_id,)
    ).fetchall()

    con.close()
    return render_template('precios.html', producto=producto, precios=precios)

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

# ------------------------------
# Iniciar servidor
# ------------------------------
if __name__ == '__main__':
    app.run(debug=True)
