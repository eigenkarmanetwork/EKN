from database_migration.versions import v1_0_0
from etn import types
from typing import Callable, TYPE_CHECKING
import warnings

if TYPE_CHECKING:
    from etn.database import DatabaseManager

main_database_versions: types.DATABASE_VERSIONS = {
    "1.0.0": None,
    "1.0.1": v1_0_0.update,
}


def update_database(database: "DatabaseManager") -> None:
    version = get_version(database)
    print(f"Current database version: {version}")
    versions = list(main_database_versions.keys())
    if version not in versions:
        warnings.warn("Database version doesn't exist in dictionary", Warning)
        return
    index = versions.index(version)
    for v in versions[index + 1:]:
        print(f"Updating database to v{v}")
        if main_database_versions[v]:  # If not None
            main_database_versions[v](database)


def get_version(database: "DatabaseManager") -> str:
    with database as db:
        result = db.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='etn_settings'")
        if not result.fetchone():
            return "1.0.0"
        result = db.execute("SELECT value FROM etn_settings WHERE setting='version'")
        value = result.fetchone()
        return value['value']
