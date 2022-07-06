from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from etn.database import DatabaseManager


def update(database: "DatabaseManager") -> None:
    with database as db:
        db.execute("CREATE TABLE IF NOT EXISTS etn_settings (setting TEXT PRIMARY KEY UNIQUE, value TEXT)")
        db.commit()
        db.execute("INSERT INTO etn_settings (setting, value) VALUES('version', '1.0.1')")
