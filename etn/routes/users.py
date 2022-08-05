from etn.database import DatabaseManager
from etn.decs import allow_cors
from etn.helpers import (
    get_params,
    verify_credentials,
    verify_credentials_hash,
    verify_service,
    resolve_service_username,
    update_session_key,
)
from flask import Response
from typing import Optional
import json
import secrets
import time


@allow_cors
def verify_credentials_route() -> Response:
    """
    Used to verify ETN user credentials, and return either a connection key, session key, or password hash.

    Message Structure:
    {
        "username": str
        "password": str
        "password_type": Optional[Literal["raw_password", "password_hash", "connection_key", "session_key"]]
        "service_name": Optional[str]
        "service_key": Optional[str]
    }
    Returns:
    403: Service name or key is incorrect.
    403: Username or Password is incorrect.
    404: Service is not connected.
    200: JSON:
    {
        "password": str
        "password_type": Literal["password_hash", "conneciton_key", "session_key"]
        "expires": int (unix timestamp or 0 if N/A)
    }
    """
    username, password, password_type, service_name, service_key = get_params(
        ["username", "password", "password_type", "service_name", "service_key"]
    )

    service_id: Optional[int] = None
    if service_name and service_key:
        service = verify_service(service_name, service_key)
        if service:
            service_id = service["id"]
        else:
            return Response("Service name or key is incorrect.", 403)

    user = verify_credentials(username, password, password_type, service_id)
    if not user:
        return Response("Username or Password is incorrect.", 403)

    session_key: Optional[str] = None
    connection_key: Optional[str] = None
    expires = 0
    if user["security"] == 0 and service_id:
        with DatabaseManager() as db:
            result = db.execute(
                "SELECT * FROM connections WHERE user=:user_id AND service=:service_id",
                {"user_id": user["id"], "service_id": service_id},
            )
            row = result.fetchone()
            if not row:
                return Response("Service is not connected.", 404)
            if row["key"]:
                connection_key = row["key"]
            else:
                # Security was set to 0 after the connection was made, generating key.
                connection_key = secrets.token_hex(16)
                db.execute(
                    "UPDATE connections SET key=:connection_key WHERE user=:user_id AND service=:service_id",
                    {"connection_key": connection_key, "user_id": user["id"], "service_id": service_id},
                )
    if user["security"] <= 1:
        with DatabaseManager() as db:
            result = db.execute("SELECT * FROM session_keys WHERE user=:user_id", {"user_id": user["id"]})
            row = result.fetchone()
            gen_key = True
            if row:
                gen_key = False
                if row["expires"] > int(time.time()):
                    session_key = row["key"]
                    expires = row["expires"]
                else:
                    session_key = secrets.token_hex(16)
                    expires = int(time.time()) + 86_400
                    db.execute(
                        "UPDATE session_keys SET key=:key, expires=:expires WHERE user=:id",
                        {"id": user["id"], "key": session_key, "expires": expires},
                    )
            if gen_key:
                session_key = secrets.token_hex(16)
                expires = int(time.time()) + 86_400
                db.execute(
                    "INSERT INTO session_keys (user, key, expires) VALUES (?, ?, ?)",
                    (user["id"], session_key, expires),
                )

    resp = {
        "password": connection_key if connection_key else session_key if session_key else user["password"],
        "password_type": "connection_key"
        if connection_key
        else "session_key"
        if session_key
        else "password_hash",
        "expires": expires if expires else 0,
    }
    return Response(json.dumps(resp), 200)


@allow_cors
def get_current_key() -> Response:
    """
    Get's the current session or connection key if it exists, otherwise returns 404.

    Message Structure:
    {
        "username": str
        "service_name": str
        "service_key": str
    }
    Returns:
    403: Service name or key is incorrect.
    404: Service is not connected.
    404: No key available.
    200: JSON:
    {
        "password": str
        "password_type": Literal["conneciton_key", "session_key"]
        "expires": int (unix timestamp or 0 if N/A)
    }
    """

    username, service_name, service_key = get_params(["username", "service_name", "service_key"])

    service = verify_service(service_name, service_key)
    if not service:
        return Response("Service name or key is incorrect.", 403)
    service_id = service["id"]

    user = resolve_service_username(service["id"], username)
    if not user:
        return Response("Service is not connected.", 404)

    session_key: Optional[str] = None
    connection_key: Optional[str] = None
    expires = 0
    if user["security"] == 0:
        with DatabaseManager() as db:
            result = db.execute(
                "SELECT * FROM connections WHERE user=:user_id AND service=:service_id",
                {"user_id": user["id"], "service_id": service_id},
            )
            row = result.fetchone()
            if row["key"]:
                connection_key = row["key"]
            else:
                # Security was set to 0 after the connection was made, generating key.
                connection_key = secrets.token_hex(16)
                db.execute(
                    "UPDATE connections SET key=:connection_key WHERE user=:user_id AND service=:service_id",
                    {"connection_key": connection_key, "user_id": user["id"], "service_id": service_id},
                )
    if user["security"] == 1:
        with DatabaseManager() as db:
            result = db.execute("SELECT * FROM session_keys WHERE user=:user_id", {"user_id": user["id"]})
            row = result.fetchone()
            if row:
                if row["expires"] > int(time.time()):
                    session_key = row["key"]
                    expires = row["expires"]

    if connection_key:
        resp = {
            "password": connection_key,
            "password_type": "connection_key",
            "expires": 0,
        }
    elif session_key:
        resp = {
            "password": session_key,
            "password_type": "session_key",
            "expires": expires,
        }
    else:
        return Response("No key available.", 404)
    return Response(json.dumps(resp), 200)


@allow_cors
def verify_credentials_hash_route() -> Response:
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
def gdpr_view() -> Response:
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
    update_session_key(username)

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
def change_security() -> Response:
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
    username, password, password_type, security = get_params(
        ["username", "password", "password_type", "security"]
    )

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
        db.execute(
            "UPDATE users SET security=:security WHERE id=:id", {"security": security, "id": user["id"]}
        )
    update_session_key(username)
    return Response("Success.", 200)
