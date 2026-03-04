
import sqlite3
import os

db_path = r'c:\Users\DELL\Desktop\smart1\attendance.db'

if not os.path.exists(db_path):
    print(f"Database not found at {db_path}")
    exit(1)

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

cursor.execute("SELECT username, role, name FROM user")
users = cursor.fetchall()

print("Users in database:")
for user in users:
    print(f"Username: {user[0]}, Role: {user[1]}, Name: {user[2]}")

conn.close()
