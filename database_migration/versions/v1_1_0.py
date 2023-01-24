from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from etn.database import DatabaseManager


def update(database: "DatabaseManager") -> None:
    with database as db:
        db.execute(
            "ALTER TABLE users ADD COLUMN security INTEGER CHECK(security IN (0, 1, 2)) DEFAULT 2"
        )
        db.execute("ALTER TABLE connections ADD COLUMN key TEXT DEFAULT NULL")
        db.execute("UPDATE etn_settings SET value='1.1.0' WHERE setting='version'")
