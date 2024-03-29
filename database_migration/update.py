from database_migration.versions import (
    v1_0_1,
    v1_1_0,
    v2_0_0,
    v2_0_1,
    v2_1_0,
    v2_1_1,
    v2_2_0,
    v2_2_1,
    v2_3_0,
)
from ekn import types
from typing import TYPE_CHECKING
import warnings

if TYPE_CHECKING:
    from ekn.database import DatabaseManager

main_database_versions: types.DATABASE_VERSIONS = {
    "1.0.0": None,
    "1.0.1": v1_0_1.update,
    "1.1.0": v1_1_0.update,
    "2.0.0": v2_0_0.update,
    "2.0.1": v2_0_1.update,
    "2.1.0": v2_1_0.update,
    "2.1.1": v2_1_1.update,
    "2.2.0": v2_2_0.update,
    "2.2.1": v2_2_1.update,
    "2.3.0": v2_3_0.update,
}


def update_database(database: "DatabaseManager") -> None:
    version = get_version(database)
    versions = list(main_database_versions.keys())
    if version not in versions:
        warnings.warn("Database version doesn't exist in dictionary", Warning)
        return
    index = versions.index(version)
    for v in versions[index + 1 :]:
        print(f"Updating database from v{version} to v{v}")
        if main_database_versions[v]:  # If not None
            main_database_versions[v](database)  # type: ignore


def get_version(database: "DatabaseManager") -> str:
    with database as db:
        result = db.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='etn_settings'"
        )
        if not result.fetchone():
            return "1.0.0"
        result = db.execute("SELECT value FROM etn_settings WHERE setting='version'")
        value = result.fetchone()
        return value["value"]
