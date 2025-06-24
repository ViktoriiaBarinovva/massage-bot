# db/helpers.py
import sqlite3

def get_services():
    conn = sqlite3.connect("massage_bot.db")
    cursor = conn.cursor()
    cursor.execute("SELECT id, name, description FROM services")
    services = cursor.fetchall()
    conn.close()
    return services