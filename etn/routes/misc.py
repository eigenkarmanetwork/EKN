from database_migration.update import get_version
from etn.database import DatabaseManager
from flask import Response


def version() -> Response:
    return Response(get_version(DatabaseManager()), 200)