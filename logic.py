import sqlite3
from datetime import datetime, timedelta

class DB_Manager:
    def __init__(self, database):
        self.database = database
    def create_tables(self):
        conn = sqlite3.connect("support.db")
        with conn:
            conn.execute('''CREATE TABLE IF NOT EXISTS users (
                         id INTEGER PRIMARY KEY AUTOINCREMENT,
                         name VARCHAR(100)
                         )''')
            conn.execute('''CREATE TABLE IF NOT EXISTS requests (
                         request_id INTEGER PRIMARY KEY,
                         user_id INTEGER,
                         text TEXT,
                         created_at DATETIME,
                         FOREIGN KEY(user_id) REFERENCES users(id)
                        )''')
            conn.commit()

    def add_user(self, tg_id, name):
        conn = sqlite3.connect(self.database)
        with conn:
            conn.execute("INSERT OR IGNORE INTO users (id, name) VALUES (?, ?)", (tg_id, name))
    
    def add_request(self, tg_id, text):
        conn = sqlite3.connect(self.database)
        with conn:
            user = conn.execute("SELECT id FROM users WHERE id = ?", (tg_id,)).fetchone()
            if user:
                conn.execute(
                    "INSERT INTO requests (user_id, text, created_at) VALUES (?, ?, ?)",
                    (user[0], text, datetime.now().isoformat())
                )
                conn.commit()
            else:
                print('Ошибка: такого пользователя не существует.')
    
    def get_all_requests(self):
        conn = sqlite3.connect(self.database)
        with conn:
            rows = conn.execute('''
                SELECT r.request_id, u.name, r.text, r.created_at
                FROM requests r
                JOIN users u ON r.user_id = u.id
                ORDER BY r.created_at DESC
            ''').fetchall()
        return rows

    def can_user_send_request(self, tg_id):
        conn = sqlite3.connect(self.database)
        with conn:
            row = conn.execute(
                "SELECT created_at FROM requests WHERE user_id = ? ORDER BY created_at DESC LIMIT 1",
                (tg_id,)
            ).fetchone()

        if row is None:
            return True  # пользователь ещё не делал запросов

        last_request_time = datetime.fromisoformat(row[0])
        now = datetime.now()

        # проверка, прошло ли больше 1 часа
        return (now - last_request_time) >= timedelta(hours=1)

DATABASE = 'support.db'

if __name__ == '__main__':
    manager = DB_Manager(DATABASE)
    manager.create_tables()
