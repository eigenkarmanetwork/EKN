from database_migration.update import update_database
from etn import types
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
        update_database(self)

    def open(self) -> None:
        self.lock.acquire()
        while not self.connected:
            self._open()

    def _open(self) -> None:
        try:
            if not os.path.isfile(self.path):
                self._create_database()
            self.conn = sqlite3.connect(self.path)
            self.conn.row_factory = sqlite3.Row
            self.cur = self.conn.cursor()
            self.connected = True
        except sqlite3.Error as e:
            print(f"Database Error: {e}")

    def close(self) -> None:
        if self.conn:
            self.conn.commit()
            if self.cur:
                self.cur.close()
            self.conn.close()
        self.conn = None
        self.cur = None
        self.connected = False
        self.lock.release()

    def __enter__(self):
        self.open()
        return self

    def __exit__(self, exc_type, exc_value, traceback) -> None:
        self.close()

    def _create_database(self) -> None:
        conn = sqlite3.connect(self.path)
        cur = conn.cursor()
        cur.execute("CREATE TABLE IF NOT EXISTS votes (user_from INTEGER, user_to INTEGER, category TEXT DEFAULT 'general', count INTEGER)")
        cur.execute("""CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT,
            password TEXT,
            salt TEXT,
            security TEXT CHECK(security in (0, 1, 2)) DEFAULT 2
        )""")
        cur.execute("CREATE TABLE IF NOT EXISTS services (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, key TEXT, salt TEXT)")
        cur.execute("CREATE TABLE IF NOT EXISTS connections (service INTEGER, service_user TEXT, user INTEGER, key TEXT DEFAULT NULL)")
        cur.execute("CREATE TABLE IF NOT EXISTS etn_settings (setting TEXT PRIMARY KEY UNIQUE, value TEXT)")
        cur.execute("CREATE TABLE IF NOT EXISTS categories (category TEXT PRIMARY KEY UNIQUE)")
        conn.commit()
        conn.execute("INSERT INTO etn_settings (setting, value) VALUES ('version', '2.0.0')")
        conn.execute("INSERT INTO categories (category) VALUES ('general')")
        conn.commit()
        cur.close()
        conn.close()
        print("Created database!")

    def execute(self, sql: str, params: types.SQL_PARAMS = None) -> sqlite3.Cursor:
        if not self.connected:
            raise RuntimeError("Cannot run execute on a closed database!")
        if params:
            return self.cur.execute(sql, params)
        return self.cur.execute(sql)

    def commit(self):
        self.conn.commit()
