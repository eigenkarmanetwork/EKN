from typing import TYPE_CHECKING
import hashlib
import secrets

if TYPE_CHECKING:
    from etn.database import DatabaseManager


def update(database: "DatabaseManager") -> None:
    with database as db:
        result = db.execute("SELECT * FROM services WHERE name='ETN'")
        if result.fetchone():
            db.execute("UPDATE services SET key=:key, salt=:salt WHERE name='ETN'",
                       {
                        "key": "833b334bb52dded02beb81bffea9f1e55f84db86363b32403" +
                               "d1e76254dfb798499f978c944519974faeeb98029bbc3f92f" +
                               "cf0eb7179d9b3ab95d12cc1a422319",
                        "salt": "dac0a578446b"
                       }
                      )
        else:
            db.execute("INSERT INTO services (name, key, salt) VALUES (?, ?, ?)",
                       (
                        "ETN",
                        "833b334bb52dded02beb81bffea9f1e55f84db86363b32403d1e76" +
                        "254dfb798499f978c944519974faeeb98029bbc3f92fcf0eb7179d" +
                        "9b3ab95d12cc1a422319",
                        "dac0a578446b"
                       )
                      )
        result = db.execute("SELECT * FROM services WHERE name='ETN'")
        etn_service_id = result.fetchone()["id"]
        result = db.execute("SELECT * FROM users")
        for user in result.fetchall():
            result = db.execute("SELECT * FROM connections WHERE service=:service AND user=:id",
                                {"service": etn_service_id, "id": user["id"]})
            if result.fetchone():
                continue
            db.execute("INSERT INTO connections (service, service_user, user) VALUES (?, ?, ?)",
                       (etn_service_id, user["username"], user["id"]))
        db.execute("UPDATE etn_settings SET value='2.0.1' WHERE setting='version'")
