from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ekn.database import DatabaseManager


def update(database: "DatabaseManager") -> None:
    with database as db:
        db.execute("ALTER TABLE votes RENAME TO votes_old")
        db.commit()
        db.execute(
            "CREATE TABLE votes (user_from INTEGER, user_to INTEGER, category TEXT DEFAULT 'general', "
            + "count INTEGER, PRIMARY KEY(user_from, user_to, category))"
        )
        db.commit()
        db.execute(
            "INSERT INTO votes SELECT user_from, user_to, category, count FROM votes_old"
        )
        db.execute("DROP TABLE IF EXISTS votes_old")
        db.execute("UPDATE etn_settings SET value='2.2.1' WHERE setting='version'")
