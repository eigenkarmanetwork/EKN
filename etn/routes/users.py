from etn.database import DatabaseManager
from etn.decs import allow_cors
from etn.helpers import get_params, verify_credentials, verify_credentials_hash
from flask import Response, request
import json
import secrets
import time


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

    resp = Response(user["password"], 200)
    if user["security"] == 1:
        with DatabaseManager() as db:
            result = db.execute("SELECT * FROM session_keys WHERE user=:user_id", {"user_id": user["id"]})
            row = result.fetchone()
            gen_key = True
            if row:
                if row["expires"] > int(time.time()):
                    gen_key = False
                    session_key = row["key"]
                    expires = row["expires"]
            if gen_key:
                session_key = secrets.token_hex(16)
                expires = int(time.time()) + 86_400
                db.execute(
                    "INSERT INTO session_keys (user, key, expires) VALUES (?, ?, ?)",
                    (user["id"], session_key, expires),
                )

        resp.set_cookie("session_key", session_key, expires=expires)

    return resp


@allow_cors
def get_session_key():
    """
    Get's the current session key from cookies if it exists, otherwise returns 404.
    """

    key = request.cookies.get("session_key")
    if key is None:
        return Response("", 404)
    return Response(key)


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


@allow_cors
def change_security():
    """
    Used to change a user's security settings.

    Message Structure:
    {
        "username": str
        "password": str
        "security": Literal[0, 1, 2]
        "password_type": Optional[Literal["raw_password", "password_hash", "connection_key", "session_key"]]
    }
    Returns:
    400: Invalid security option.
    403: Username or Password is incorrect.
    200: Success.
    """
    username, password, password_type, security = get_params(["username", "password", "password_type", "security"])

    try:
        security = int(security)
    except ValueError:
        return Response("Invalid security option.", 400)

    user = verify_credentials(username, password, password_type)
    if not user:
        return Response("Username or Password is incorrect.", 403)

    if security not in [0, 1, 2]:
        return Response("Invalid security option.", 400)

    with DatabaseManager() as db:
        db.execute("UPDATE users SET security=:security WHERE id=:id", {"security": security, "id": user["id"]})
    return Response("Success.", 200)
