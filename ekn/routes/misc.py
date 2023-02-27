from database_migration.update import get_version
from ekn.database import DatabaseManager
from ekn.decs import allow_cors
from flask import Response


def version() -> Response:
    """Get the current EKN version
    ---
    responses:
        200:
            description: The current version
    """
    return Response(get_version(DatabaseManager()), 200)


def count_rows(where):
    with DatabaseManager() as db:
        result = db.execute(f"SELECT COUNT(*) FROM {where};")
        row = result.fetchone()
        if row:
            return Response(str(row["COUNT(*)"]), 200)
        return Response("0", 200)


@allow_cors(hosts=["*"])
def get_total_users() -> Response:
    """Get total number of users in the system
    Returns the total users recorded in EKN, including temporary and real/registered users.
    ---
    responses:
        200:
            description: The total number of users
    """
    return count_rows('users')


@allow_cors(hosts=["*"])
def get_total_real_users() -> Response:
    """Get total number of real users in the system
    Returns the total users recorded in EKN, excluding temp users.
    ---
    responses:
        200:
            description: The total number of real users
    """
    return count_rows('users WHERE temp=0')


@allow_cors(hosts=["*"])
def get_total_temp_users() -> Response:
    """Get total number of temporary users in the system
    Returns the total users recorded in EKN, excluding real/registered users.
    ---
    responses:
        200:
            description: The total number of temporary users
    """
    return count_rows('users WHERE temp=1')


@allow_cors(hosts=["*"])
def get_total_votes() -> Response:
    """Get total number of votes in the system
    Returns the total number of votes recorded in EKN.
    ---
    responses:
        200:
            description: The total number of votes
    """
    return count_rows('votes')
