from etn.database import DatabaseManager
from etn.decs import allow_cors
from etn.helpers import get_params, verify_service, verify_credentials
from flask import Response
from typing import Optional
import hashlib
import json
import secrets
import time


@allow_cors
def register_user() -> Response:
    """
    Message Structure:
    {
        "username": str
        "password": str
    }

    Returns:
    409: Username is not available.
    409: Invalid Username.
    200: Registration Successful.
    """
    username, password = get_params(["username", "password"])
    if ":" in username:
        # Colon not allowed to ensure unique usernames for temp users
        return Response("Invalid Username", 409)

    salt = secrets.token_hex(6)
    sha512 = hashlib.new("sha512")
    sha512.update(f"{password}:{salt}".encode("utf8"))
    password_hash = sha512.hexdigest()
    with DatabaseManager() as db:
        result = db.execute(
            "SELECT * FROM users WHERE username=:username", {"username": username}
        )
        if result.fetchone():
            return Response("Username is not available.", 409)  # 409: Conflict
        db.execute(
            "INSERT INTO users (username, password, salt) VALUES (?, ?, ?)",
            (username, password_hash, salt),
        )
        result = db.execute(
            "SELECT * FROM users WHERE username=:username", {"username": username}
        )
        id = result.fetchone()["id"]
        db.execute(
            "INSERT INTO connections (service, service_user, user) VALUES (?, ?, ?)",
            (db.etn_service_id, username, id),
        )
    return Response("Registration Successful.", 200)


@allow_cors(hosts=["*"])
def register_temp_user() -> Response:
    """
    Message Structure:
    {
        "service_user": str (Service Username)
        "service_name": str
        "service_key": str
    }

    Returns:
    403: Service name or key is incorrect.
    409: Username is not available.
    200: Registration Successful.
    """
    service_user, service, key = get_params(
        ["service_user", "service_name", "service_key"]
    )
    username = f"{service}:{service_user}"  # Helps keep username unique
    service_obj = verify_service(service, key)
    if not service_obj:
        return Response("Service name or key is incorrect.", 403)
    service_id = service_obj["id"]

    with DatabaseManager() as db:
        result = db.execute(
            "SELECT * FROM users WHERE username=:username", {"username": username}
        )
        if result.fetchone():
            return Response("Username is not available.", 409)
        db.execute(
            "INSERT INTO users (username, password, salt, temp) VALUES (?, ?, ?, ?)",
            (username, None, None, 1),
        )
        result = db.execute(
            "SELECT * FROM users WHERE username=:username", {"username": username}
        )
        id = result.fetchone()["id"]
        db.execute(
            "INSERT INTO connections (service, service_user, user) VALUES (?, ?, ?)",
            (service_id, service_user, id),
        )
    return Response("Registration Successful.", 200)


@allow_cors
def register_service() -> Response:
    """
    Message Structure:
    {
        "name": str
    }

    Returns:
    409: Name is not available.
    200: key: str
    """
    name = get_params(["name"])

    with DatabaseManager() as db:
        result = db.execute("SELECT * FROM services WHERE name=:name", {"name": name})
        if result.fetchone():
            return Response("Name is not available.", 409)
        key = secrets.token_hex(16)
        salt = secrets.token_hex(6)
        sha512 = hashlib.new("sha512")
        sha512.update(f"{key}:{salt}".encode("utf8"))
        key_hash = sha512.hexdigest()
        db.execute(
            "INSERT INTO services (name, key, salt) VALUES (?, ?, ?)",
            (name, key_hash, salt),
        )
        return Response(key, 200)


@allow_cors(hosts=["*"])
def register_connection() -> Response:
    """
    Register's a connection, or updates the connection if it already exists.

    Message Structure:
    {
        "service_name": str (Service's name)
        "service_key": str (Service's key)
        "service_user": str (Username on Service)
        "username": str (Username on ETN)
        "password": str (Password on ETN)
        "password_type": Optional[Literal["raw_password", "password_hash", "connection_key", "session_key"]]
    }

    Returns:
    403: Service name or key is incorrect.
    403: Username or Password is incorrect.
    409: Service user already connected to the ETN.
    200: JSON:
    {
        "password": str
        "password_type": Literal["password_hash", "conneciton_key", "session_key"]
        "expires": int (unix timestamp or 0 if N/A)
    }
    """
    service, key, service_user, username, password, password_type = get_params(
        [
            "service_name",
            "service_key",
            "service_user",
            "username",
            "password",
            "password_type",
        ]
    )

    service_obj = verify_service(service, key)
    if not service_obj:
        return Response("Service name or key is incorrect.", 403)
    service_id = service_obj["id"]

    user = verify_credentials(username, password, password_type, service_id)
    if not user:
        return Response("Username or Password is incorrect.", 403)

    with DatabaseManager() as db:
        result = db.execute(
            "SELECT * FROM connections WHERE service_user=:service_user AND service=:service_id",
            {"service_user": service_user, "service_id": service_id},
        )
        row = result.fetchone()
        if not row:
            db.execute(
                "INSERT INTO connections (service, service_user, user) VALUES (?, ?, ?)",
                (service_id, service_user, user["id"]),
            )
        else:
            # Possibly a temp account!
            temp_user_id = int(row["user"])
            result = db.execute(
                "SELECT * FROM users WHERE id=:id", {"id": temp_user_id}
            )
            temp_user = result.fetchone()
            if not temp_user:
                raise RuntimeError(
                    "Service user is connected to a non existant account"
                )
            if int(temp_user["temp"]) == 0:
                return Response("Service user already connected to the ETN.", 409)
            # Temp account found! Migrating...
            db.execute(
                "UPDATE votes SET user_from=:new_id WHERE user_from=:temp_id",
                {"new_id": user["id"], "temp_id": temp_user_id},
            )
            db.execute(
                "UPDATE votes SET user_to=:new_id WHERE user_to=:temp_id",
                {"new_id": user["id"], "temp_id": temp_user_id},
            )
            db.execute(
                "DELETE FROM users WHERE id=:id and temp=1", {"id": temp_user_id}
            )
            db.execute(
                "DELETE FROM connections WHERE user=:id and service=:service_id",
                {"id": temp_user_id, "service_id": service_id},
            )
            db.execute(
                "INSERT INTO connections (service, service_user, user) VALUES (?, ?, ?)",
                (service_id, service_user, user["id"]),
            )
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
            if not row:
                return Response("Service is not connected.", 500)
            if row["key"]:
                connection_key = row["key"]
            else:
                # Security was set to 0 after the connection was made, generating key.
                connection_key = secrets.token_hex(16)
                db.execute(
                    "UPDATE connections SET key=:connection_key WHERE user=:user_id AND service=:service_id",
                    {
                        "connection_key": connection_key,
                        "user_id": user["id"],
                        "service_id": service_id,
                    },
                )
    if user["security"] == 1:
        with DatabaseManager() as db:
            result = db.execute(
                "SELECT * FROM session_keys WHERE user=:user_id",
                {"user_id": user["id"]},
            )
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
        "password": connection_key
        if connection_key
        else session_key
        if session_key
        else user["password"],
        "password_type": "connection_key"
        if connection_key
        else "session_key"
        if session_key
        else "password_hash",
        "expires": expires if expires else 0,
    }
    return Response(json.dumps(resp), 200)
