from typing import TYPE_CHECKING
import hashlib
import secrets

if TYPE_CHECKING:
    from etn.database import DatabaseManager


def update(database: "DatabaseManager") -> None:
    with database as db:
        db.execute("CREATE TABLE IF NOT EXISTS categories (category TEXT PRIMARY KEY UNIQUE)")
        db.execute("ALTER TABLE services ADD COLUMN salt TEXT")
        db.commit()
        result = db.execute("SELECT * FROM services")
        for service in result.fetchall():
            salt = secrets.token_hex(6)
            sha512 = hashlib.new("sha512")
            old_key = service["key"]
            sha512.update(f"{old_key}:{salt}".encode('utf8'))
            new_key = sha512.hexdigest()
            db.execute("UPDATE services SET key=:new_key, salt=:salt WHERE id=:id",
                       {"new_key": new_key, "salt": salt, "id": service["id"]})
        db.execute("INSERT INTO categories (category) VALUES ('general')")
        db.execute("ALTER TABLE votes ADD COLUMN category TEXT DEFAULT 'general'")
        db.execute("UPDATE etn_settings SET value='2.0.0' WHERE setting='version'")
