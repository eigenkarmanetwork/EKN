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
        self._get_etn_service()

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
        cur.execute(
            "CREATE TABLE IF NOT EXISTS votes (user_from INTEGER, user_to INTEGER, category TEXT DEFAULT 'general', count INTEGER)"
        )
        cur.execute(
            """CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT,
            password TEXT,
            salt TEXT,
            security TEXT CHECK(security in (0, 1, 2)) DEFAULT 2
        )"""
        )
        cur.execute(
            "CREATE TABLE IF NOT EXISTS services (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, key TEXT, salt TEXT)"
        )
        cur.execute(
            "CREATE TABLE IF NOT EXISTS connections (service INTEGER, service_user TEXT, user INTEGER, key TEXT DEFAULT NULL)"
        )
        cur.execute("CREATE TABLE IF NOT EXISTS etn_settings (setting TEXT PRIMARY KEY UNIQUE, value TEXT)")
        cur.execute("CREATE TABLE IF NOT EXISTS categories (category TEXT PRIMARY KEY UNIQUE)")
        cur.execute(
            "CREATE TABLE IF NOT EXISTS session_keys (user INTEGER PRIMARY KEY, key TEXT, expires INTEGER)"
        )
        conn.commit()
        cur.execute("INSERT INTO etn_settings (setting, value) VALUES ('version', '2.1.0')")
        cur.execute("INSERT INTO categories (category) VALUES ('general')")
        cur.execute(
            "INSERT INTO services (name, key, salt) VALUES (?, ?, ?)",
            (
                "ETN",
                "833b334bb52dded02beb81bffea9f1e55f84db86363b32403d1e76"
                + "254dfb798499f978c944519974faeeb98029bbc3f92fcf0eb7179d"
                + "9b3ab95d12cc1a422319",
                "dac0a578446b",
            ),
        )
        conn.commit()
        cur.close()
        conn.close()
        print("Created database!")

    def _get_etn_service(self) -> None:
        conn = sqlite3.connect(self.path)
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        result = cur.execute("SELECT * FROM services WHERE name='ETN'")
        self.etn_service_obj = result.fetchone()
        self.etn_service_id = self.etn_service_obj["id"]
        assert self.etn_service_obj, "ETN Service Does Not Exist!"
        cur.close()
        conn.close()

    def execute(self, sql: str, params: types.SQL_PARAMS = None) -> sqlite3.Cursor:
        if not self.connected:
            raise RuntimeError("Cannot run execute on a closed database!")
        if params:
            return self.cur.execute(sql, params)
        return self.cur.execute(sql)

    def commit(self):
        self.conn.commit()
