from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from etn.database import DatabaseManager


def update(database: "DatabaseManager") -> None:
    with database as db:
        db.execute("ALTER TABLE users RENAME TO users_old")
        db.commit()
        db.execute(
            "CREATE TABLE users (id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT, password TEXT, "
            + "salt TEXT, security INTEGER CHECK(security in (0, 1, 2)) DEFAULT 0)"
        )
        db.commit()
        result = db.execute("SELECT * FROM users_old")
        for row in result.fetchall():
            db.execute(
                "INSERT INTO users (id, username, password, salt, security) VALUES (?, ?, ?, ?, ?)",
                (
                    row["id"],
                    row["username"],
                    row["password"],
                    row["salt"],
                    # If security was set to 1, keep it.  Otherwise set to 0.
                    row["security"] if row["security"] == 1 else 0,
                ),
            )
        db.commit()
        db.execute("DROP TABLE users_old")
        db.execute("UPDATE etn_settings SET value='2.1.1' WHERE setting='version'")
