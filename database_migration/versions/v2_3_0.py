from typing import TYPE_CHECKING
import json

if TYPE_CHECKING:
    from etn.database import DatabaseManager


def update(database: "DatabaseManager") -> None:
    with database as db:
        db.execute(
            "ALTER TABLE categories ADD COLUMN type TEXT CHECK(type in ('normal', 'secondary', 'composite', 'general')) DEFAULT 'normal'"
        )
        db.execute("ALTER TABLE categories ADD COLUMN secondary_of TEXT")
        db.execute("ALTER TABLE categories ADD COLUMN composite_of TEXT")
        db.execute("ALTER TABLE categories ADD COLUMN description TEXT")
        db.commit()
        # "INSERT INTO categories (category, type, secondary_of, description) VALUES (?, ?, ?, ?)",
        # "INSERT INTO categories (category, type, composite_of, description) VALUES (?, ?, ?, ?)",
        # "INSERT INTO categories (category, type, description) VALUES (?, ?, ?)",
        db.execute("UPDATE categories SET type='general' WHERE category='general'")
        db.execute(
            "INSERT INTO categories (category, type, description) VALUES (?, ?, ?)",
            (
                "agi safety research",
                "normal",
                "Assign this flavor to nodes which have produced research which makes it more likely "
                + "that humanity will solve the AI control problem, resulting in an aligned "
                + "superintelligence.",
            ),
        )
        db.execute(
            "INSERT INTO categories (category, type, secondary_of, description) VALUES (?, ?, ?, ?)",
            (
                "agi safety ecosystem development",
                "secondary",
                "agi safety research",
                "Assign this flavor to nodes which have provided value to you as a researcher "
                + "or other researchers by improving the ecosystem (outreach, training, "
                + "support, conferences, coaching, accommodation, etc).",
            ),
        )
        db.execute(
            "INSERT INTO categories (category, type, composite_of, description) VALUES (?, ?, ?, ?)",
            (
                "agi safety",
                "composite",
                json.dumps(["agi safety research", "agi safety ecosystem development"]),
                "Assign this flavor to nodes who you trust in the field of AGI Safety.",
            ),
        )
        db.execute(
            "INSERT INTO categories (category, type, description) VALUES (?, ?, ?)",
            (
                "bounty ecosystem participation",
                "normal",
                "Assign this flavor to nodes who you trust to participate in bounties in good faith. "
                + "This includes providing good work to claim a bounty, as well as providing payment "
                + "for bounties set by them.",
            ),
        )
        db.execute("UPDATE etn_settings SET value='2.3.0' WHERE setting='version'")
