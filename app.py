import os
import sqlite3
import psycopg2
from flask import Flask, render_template, request, redirect, url_for

app = Flask(__name__)

# ==============================
# 🔌 CONEXIÓN A BASE DE DATOS
# ==============================
def conectar():
    database_url = os.environ.get("DATABASE_URL")

    if database_url:
        # Render usa PostgreSQL
        conn = psycopg2.connect(database_url)
        print("✅ Conectado a PostgreSQL en Render")
    else:
        # Local usa SQLite
        conn = sqlite3.connect("precios.db")
        print("✅ Conectado a SQLite localmente")
    return conn


# ==============================
# ⚙️ EJECUTAR CONSULTAS SQL
# ==============================
def ejecutar_sql(conn, sql, params=None, fetch=False):
    try:
        cur = conn.cursor()

        # Determinar si es SQLite o PostgreSQL
        if isinstance(conn, sqlite3.Connection):
            placeholder = "?"
        else:
            placeholder = "%s"

        # Reemplazar placeholders si es necesario
        if params and placeholder == "?":
            sql = sql.replace("%s", "?")

        cur.execute(sql, params or [])

        if fetch:
            resultado = cur.fetchall()
        else:
            resultado = None

        conn.commit()
        cur.close()
        return resultado

    except Exception as e:
        print(f"❌ Error al ejecutar SQL: {e}")
        conn.rollback()
        return None


# ==============================
# 🏗️ CREAR TABLAS SI NO EXISTEN
# ==============================
def crear_tablas():
    conn = conectar()
    cur = conn.cursor()

    # 🔥 Elimina la tabla si ya existe
    cur.execute("DROP TABLE IF EXISTS productos")

    # Crea la tabla con la nueva estructura
    cur.execute("""
        CREATE TABLE productos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre TEXT NOT NULL,
            descripcion TEXT,
            precio_caja REAL NOT NULL,
            unidades_por_caja INTEGER NOT NULL,
            precio_unitario REAL NOT NULL
        )
    """)
    conn.commit()
    conn.close()


# ==============================
# 🏠 RUTA PRINCIPAL
# ==============================
@app.route("/")
def index():
    conn = conectar()
    productos = ejecutar_sql(conn, "SELECT * FROM productos", fetch=True)
    conn.close()
    return render_template("index.html", productos=productos)


# ==============================
# ➕ AÑADIR PRODUCTO
# ==============================
@app.route('/agregar', methods=['GET', 'POST'])
def agregar():
    if request.method == 'POST':
        nombre = request.form.get('nombre')
        descripcion = request.form.get('descripcion')
        precio_caja = request.form.get('precio_caja', type=float)
        unidades_por_caja = request.form.get('unidades_por_caja', type=int)

        if not nombre or not precio_caja or not unidades_por_caja:
            return "Faltan campos obligatorios", 400

        precio_unitario = precio_caja / unidades_por_caja

        conn = conectar()
        cur = conn.cursor()

        # Detectar si estamos usando SQLite o PostgreSQL
        try:
            cur.execute("""
                INSERT INTO productos (nombre, descripcion, precio_caja, unidades_por_caja, precio_unitario)
                VALUES (%s, %s, %s, %s, %s)
            """, (nombre, descripcion, precio_caja, unidades_por_caja, precio_unitario))
        except Exception:
            cur.execute("""
                INSERT INTO productos (nombre, descripcion, precio_caja, unidades_por_caja, precio_unitario)
                VALUES (?, ?, ?, ?, ?)
            """, (nombre, descripcion, precio_caja, unidades_por_caja, precio_unitario))

        conn.commit()
        conn.close()

        return redirect('/')
    
    # Renderizar el formulario
    return render_template('agregar.html')
# ==============================
# 🗑️ ELIMINAR PRODUCTO
# ==============================
@app.route("/eliminar/<int:id>")
def eliminar(id):
    conn = conectar()
    ejecutar_sql(conn, "DELETE FROM productos WHERE id = %s", (id,))
    conn.close()
    return redirect(url_for("index"))


# ==============================
# 🚀 INICIO DE LA APLICACIÓN
# ==============================
if __name__ == "__main__":
    crear_tablas()
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)
