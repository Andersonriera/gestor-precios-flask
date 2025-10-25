import sqlite3

conn = sqlite3.connect("productos.db")
cur = conn.cursor()

cur.execute("PRAGMA table_info(productos);")
for col in cur.fetchall():
    print(col)

conn.close()
