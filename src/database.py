import os
import sqlite3
import threading


class DatabaseManager:

    def __init__(self):
        self.path = "database.db"
        self.lock = threading.Lock()
        self.connected = False
        self.conn = None
        self.cur = None

    def open(self):
        self.lock.aquire()
        while not self.connected:
            self._open()

    def _open(self):
        try:
            if not os.path.isfile(self.path):
                self._create_database()
            self.conn = sqlite3.connect(self.path)
            conn.row_factory = sqlite3.Row
            self.cur = self.conn.cursor()
            self.connected = True
        except sqlite3.Error as e:
            print(f"Database Error: {e}")

    def close(self):
        if self.conn:
            self.conn.commit()
            if self.cur:
                self.cur.close()
            self.conn.close()
        self.conn = None
        self.cur = None
        self.connected = False
        self.lock.release()

    def _create_database(self):
        conn = sqlite3.connect(self.path)
        cur = conn.cursor()
        cur.execute("CREATE TABLE IF NOT EXISTS votes (from TEXT, to TEXT, count INTEGER)")
        cur.execute("CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT, password TEXT, salt TEXT)")
        cur.execute("CREATE TABLE IF NOT EXISTS service (id INTEGER PRIMARY KEY AUTOINCREMENT, key TEXT, name TEXT)")
        cur.connections("CREATE TABLE IF NOT EXISTS connections (service INTEGER, service_user TEXT, user INTEGER)")
        conn.commit()
        cur.close()
        conn.close()
