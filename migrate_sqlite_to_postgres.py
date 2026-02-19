import sqlite3
import psycopg2

# Connect to SQLite
sqlite_conn = sqlite3.connect('db.sqlite3')
sqlite_cur = sqlite_conn.cursor()

# Connect to Postgres
pg_conn = psycopg2.connect(
    dbname="postgresql_adewale",
    user="postgresql_adewale_user",
    password="XSSdK3qyuRRYJwehbe57FVeWrVUbBKK7",
    host="dpg-d6bd4sfgi27c73d894i0-a.postgres.render.com",
    port="5432"
)
pg_cur = pg_conn.cursor()

# Example: migrate a table called 'users'
sqlite_cur.execute("SELECT id, username, email FROM auth_user")
for row in sqlite_cur.fetchall():
    pg_cur.execute(
        "INSERT INTO auth_user (id, username, email) VALUES (%s, %s, %s) ON CONFLICT (id) DO NOTHING",
        row
    )

pg_conn.commit()
pg_cur.close()
pg_conn.close()
sqlite_cur.close()
sqlite_conn.close()

print("Migration done!")
