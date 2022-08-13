from database_migration.update import get_version
from etn.database import DatabaseManager
from etn.decs import allow_cors
from flask import Response


def version() -> Response:
    return Response(get_version(DatabaseManager()), 200)


@allow_cors(hosts=["*"])
def get_total_users() -> Response:
    with DatabaseManager() as db:
        result = db.execute("SELECT COUNT(*) FROM users;")
        row = result.fetchone()
        if row:
            return Response(str(row["COUNT(*)"]), 200)
        return Response("0", 200)


@allow_cors(hosts=["*"])
def get_total_real_users() -> Response:
    with DatabaseManager() as db:
        result = db.execute("SELECT COUNT(*) FROM users WHERE temp=0;")
        row = result.fetchone()
        if row:
            return Response(str(row["COUNT(*)"]), 200)
        return Response("0", 200)


@allow_cors(hosts=["*"])
def get_total_temp_users() -> Response:
    with DatabaseManager() as db:
        result = db.execute("SELECT COUNT(*) FROM users WHERE temp=1;")
        row = result.fetchone()
        if row:
            return Response(str(row["COUNT(*)"]), 200)
        return Response("0", 200)


@allow_cors(hosts=["*"])
def get_total_votes() -> Response:
    with DatabaseManager() as db:
        result = db.execute('SELECT SUM("count") FROM votes;')
        row = result.fetchone()
        if row:
            return Response(str(row['SUM("count")']), 200)
        return Response("0", 200)
