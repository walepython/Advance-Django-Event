import sqlite3

# Connect to your SQLite database
conn = sqlite3.connect('db.sqlite3')

# Open a file to write the SQL dump
with open('dump.sql', 'w', encoding='utf-8') as f:
    for line in conn.iterdump():
        f.write(f'{line}\n')

conn.close()
print("SQLite dump complete! File created: dump.sql")
