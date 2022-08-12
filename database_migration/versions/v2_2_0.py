from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from etn.database import DatabaseManager


def update(database: "DatabaseManager") -> None:
    with database as db:
        db.execute("ALTER TABLE users ADD COLUMN temp INTEGER DEFAULT 0")
        db.execute("UPDATE etn_settings SET value='2.2.0' WHERE setting='version'")
