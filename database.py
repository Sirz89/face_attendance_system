import sqlite3

def init_db():
    conn = sqlite3.connect("attendance.db")
    cursor = conn.cursor()
    
    # Таблица преподавателей
    cursor.execute('''CREATE TABLE IF NOT EXISTS teachers 
                      (id INTEGER PRIMARY KEY, login TEXT, password TEXT)''')
    
    # Таблица посещаемости
    cursor.execute('''CREATE TABLE IF NOT EXISTS attendance 
                      (id INTEGER PRIMARY KEY, student_name TEXT, date TEXT, teacher_id INTEGER)''')
    
    # Добавим тестового юзера, если таблица пуста
    cursor.execute("INSERT OR IGNORE INTO teachers (id, login, password) VALUES (1, 'admin', '12345')")
    
    conn.commit()
    conn.close()

if __name__ == "__main__":
    init_db()
    print("✅ База данных инициализирована.")