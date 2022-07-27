from etn.database import DatabaseManager
from etn.decs import allow_cors
from etn.helpers import get_params, verify_credentials, verify_credentials_hash
from flask import Response, request
from werkzeug.datastructures import Headers
import hashlib
import json


@allow_cors
def verify_credentials_route():
    """
    Used to verify ETN user credentials for website login, or other purposes.

    Message Structure:
    {
        "username": str
        "password": str
        "password_type": Optional[Literal["raw_password", "password_hash", "connection_key", "session_key"]]
    }
    Returns:
    403: Username or Password is incorrect.
    200: Password Hash (SHA512)
    """
    username, password, password_type = get_params(["username", "password", "password_type"])

    user = verify_credentials(username, password, password_type)
    if not user:
        return Response("Username or Password is incorrect.", 403)

    return Response(user["password"], 200)


@allow_cors
def verify_credentials_hash_route():
    """
    DEPRECATED
    Use verify_credentials instead.

    Used to verify ETN user credentials for website login, or other purposes.

    Message Structure:
    {
        "username": str
        "password": str
    }
    Returns:
    403: Username or Password is incorrect.
    200: Success.
    """
    username, password = get_params(["username", "password"])

    user = verify_credentials_hash(username, password)
    if not user:
        return Response("Username or Password is incorrect.", 403)

    return Response("Success.", 200)


@allow_cors
def gdpr_view():
    """
    Used to pull all data we have on a user in compliance with GDPR.

    Message Structure:
    {
        "username": str
        "password": str
        "password_type": Optional[Literal["raw_password", "password_hash", "connection_key", "session_key"]]
    }
    Returns:
    403: Username or Password is incorrect.
    200: JSON List of every row of data.
    """
    username, password, password_type = get_params(["username", "password", "password_type"])

    user = verify_credentials(username, password, password_type)
    if not user:
        return Response("Username or Password is incorrect.", 403)

    rows = []
    with DatabaseManager() as db:
        row = {}
        for key in user.keys():
            row[key] = user[key]
        rows.append(row)

        result = db.execute("SELECT * FROM connections WHERE user=:id", {"id": user["id"]})
        for raw_row in result.fetchall():
            row = {}
            for key in raw_row.keys():
                row[key] = raw_row[key]
            rows.append(row)

        result = db.execute("SELECT * FROM votes WHERE user_from=:id", {"id": user["id"]})
        for raw_row in result.fetchall():
            row = {}
            for key in raw_row.keys():
                row[key] = raw_row[key]
            rows.append(row)

    return Response(json.dumps(rows))
