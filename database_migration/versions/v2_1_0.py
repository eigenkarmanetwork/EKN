from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from etn.database import DatabaseManager


def update(database: "DatabaseManager") -> None:
    with database as db:
        db.execute(
            "CREATE TABLE IF NOT EXISTS session_keys (user INTEGER PRIMARY KEY, key TEXT, expires INTEGER)"
        )
        db.execute("UPDATE etn_settings SET value='2.1.0' WHERE setting='version'")
