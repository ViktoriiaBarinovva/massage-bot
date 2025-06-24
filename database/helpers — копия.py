import sqlite3

def get_services():
    conn = sqlite3.connect("massage_bot.db")
    cursor = conn.cursor()
    cursor.execute("SELECT id, name FROM services")
    services = cursor.fetchall()
    conn.close()
    return services

def get_service_info(service_id):
    conn = sqlite3.connect("massage_bot.db")
    cursor = conn.cursor()
    cursor.execute("SELECT description, price FROM services WHERE id = ?", (service_id,))
    info = cursor.fetchone()
    conn.close()
    return info

def get_available_dates(service_id):
    conn = sqlite3.connect("massage_bot.db")
    cursor = conn.cursor()
    cursor.execute("SELECT DISTINCT date FROM schedule WHERE service_id = ? AND is_booked = 0", (service_id,))
    dates = cursor.fetchall()
    conn.close()
    return [d[0] for d in dates]

def get_available_times(service_id, date):
    conn = sqlite3.connect("massage_bot.db")
    cursor = conn.cursor()
    cursor.execute("SELECT id, time FROM schedule WHERE service_id = ? AND date = ? AND is_booked = 0", (service_id, date))
    times = cursor.fetchall()
    conn.close()
    return times

def book_slot(slot_id):
    conn = sqlite3.connect("massage_bot.db")
    cursor = conn.cursor()
    cursor.execute("UPDATE schedule SET is_booked = 1 WHERE id = ?", (slot_id,))
    conn.commit()
    conn.close()
