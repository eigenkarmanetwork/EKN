from ekn.database import DatabaseManager
from ekn.decs import allow_cors
from ekn.helpers import (
    get_params,
    verify_credentials,
    verify_service,
    resolve_service_username,
    update_session_key,
)
from flask import Response
from typing import Optional
import hashlib
import json
import secrets
import time


@allow_cors
def verify_credentials_route() -> Response:
    """Used to verify EKN user credentials, and return either a connection key, session key, or password hash.
    ---
    consumes:
    - application/json
    parameters:
    - in: body
      name: service
      description: Credentials to be verified.
      schema:
        type: object
        required:
          - username
          - password
        properties:
          service_name:
            type: string
            description: The name of the service
            example: Discord
          service_key:
            type: string
            description: The key of the service
            example: d7cedfcc6670340680755685b3ae6642
          username:
            type: string
            description: The username on EKN
            example: mr_blobby
          password:
            type: string
            description: The password on EKN
            example: hunter2
          password_type:
            type: string
            description: The type of password
            enum: [raw_password, password_hash, connection_key, session_key]
            default: raw_password
    responses:
        200:
          description: Verification Successful
          content:
            application/json:
              schema:
                type: object
                properties:
                  password:
                    type: string
                    example: 2ab96390c7dbe3439de74d0c9b0b1767
                  password_type:
                    type: string
                    enum: [password_hash, connection_key, session_key]
                  expires:
                    type: integer
                    description: Posix timestamp or 0 if N/A
        403:
          description: Service name or key is incorrect / Username or Password is incorrect
        409:
          description: Service user already connected to the EKN
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
                    {
                        "connection_key": connection_key,
                        "user_id": user["id"],
                        "service_id": service_id,
                    },
                )
    if user["security"] <= 1:
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


@allow_cors
def get_current_key() -> Response:
    """Get's the current session or connection key if it exists, otherwise returns 404.
    Allows a service to get a connection key or session key of a connected user. `username` should be the username or your service, and is case sensitive.
    ---
    consumes:
    - application/json
    parameters:
    - in: body
      name: service
      description: Credentials to be verified.
      schema:
        type: object
        required:
          - username
          - service_name
          - service_key
        properties:
          service_name:
            type: string
            description: The name of the service
            example: Discord
          service_key:
            type: string
            description: The key of the service
            example: a4b4da38aa385015769b44de37651a51
          username:
            type: string
            description: The username on EKN
            example: mr_blobby
    responses:
        200:
          description: Session/Connection key found
          content:
            application/json:
              schema:
                type: object
                properties:
                  password:
                      type: string
                      example: 2ab96390c7dbe3439de74d0c9b0b1767
                  password_type:
                      type: string
                      enum: [password_hash, connection_key, session_key]
                  expires:
                      type: integer
                      description: Posix timestamp or 0 if N/A
        403:
          description: Service name or key is incorrect / Service is not connected
        404:
          description: No key available
    """
    username, service_name, service_key = get_params(
        ["username", "service_name", "service_key"]
    )

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
def change_password() -> Response:
    """Used to change a user's EKN password.
    ---
    consumes:
    - application/json
    parameters:
    - in: body
      name: service
      description: User credentials
      schema:
        type: object
        required:
          - username
          - password
          - new_password
        properties:
          username:
            type: string
            description: The username on EKN
            example: mr_blobby
          password:
            type: string
            description: The current password
            example: hunter2
          new_password:
            type: string
            description: The new password
            example: I_love_mama
    responses:
        200:
          description: Success
        403:
          description: Username or Password is incorrect
    """
    username, password, new_password = get_params(
        ["username", "password", "new_password"]
    )

    user = verify_credentials(username, password, password_type="raw_password")
    if not user:
        return Response("Username or Password is incorrect.", 403)

    salt = secrets.token_hex(6)
    sha512 = hashlib.new("sha512")
    sha512.update(f"{new_password}:{salt}".encode("utf8"))
    password_hash = sha512.hexdigest()
    with DatabaseManager() as db:
        db.execute(
            "UPDATE users SET password=:password, salt=:salt WHERE id=:id",
            {"password": password_hash, "salt": salt, "id": user["id"]},
        )

    return Response("Success.", 200)


@allow_cors
def gdpr_view() -> Response:
    """Used to pull all data we have on a user in compliance with GDPR.
    ---
    consumes:
    - application/json
    parameters:
    - in: body
      name: service
      description: User credentials
      schema:
        type: object
        required:
          - username
          - password
          - password_type
        properties:
          username:
            type: string
            description: The username on EKN
            example: mr_blobby
          password:
            type: string
            description: The current password
            example: hunter2
          password_type:
            type: string
            description: The type of password
            enum: [raw_password, password_hash, connection_key, session_key]
            default: raw_password
    responses:
        200:
          description: List of every row of data
          content:
            application/json:
              schema:
                type: array
                items:
                  type: object
        403:
          description: Username or Password is incorrect
    """
    username, password, password_type = get_params(
        ["username", "password", "password_type"]
    )

    user = verify_credentials(username, password, password_type)
    if not user:
        return Response("Username or Password is incorrect.", 403)
    update_session_key(username)

    rows = []
    with DatabaseManager() as db:
        row = dict(user)
        del row["password"]
        del row["salt"]
        rows.append(row)

        result = db.execute(
            "SELECT * FROM connections WHERE user=:id", {"id": user["id"]}
        )
        for raw_row in result.fetchall():
            row = dict(raw_row)
            rows.append(row)

        result = db.execute(
            "SELECT * FROM votes WHERE user_from=:id", {"id": user["id"]}
        )
        for raw_row in result.fetchall():
            row = dict(raw_row)
            rows.append(row)

    return Response(json.dumps(rows))


@allow_cors
def change_security() -> Response:
    """Used to change a user's security settings.
    ---
    consumes:
    - application/json
    parameters:
    - in: body
      name: service
      description: User credentials
      schema:
        type: object
        required:
          - username
          - password
          - security
        properties:
          username:
            type: string
            description: The username on EKN
            example: mr_blobby
          password:
            type: string
            description: The current password
            example: hunter2
          security:
            type: integer
            enum: [0, 1, 2]
            description: Security level
    responses:
        200:
          description: Success
        400:
          description: Invalid security option
        403:
          description: Username or Password is incorrect
    """
    username, password, security = get_params(
        ["username", "password", "security"]
    )

    try:
        security = int(security)
    except ValueError:
        return Response("Invalid security option.", 400)

    user = verify_credentials(username, password, password_type="raw_password")
    if not user:
        return Response("Username or Password is incorrect.", 403)

    if security not in [0, 1, 2]:
        return Response("Invalid security option.", 400)

    with DatabaseManager() as db:
        db.execute(
            "UPDATE users SET security=:security WHERE id=:id",
            {"security": security, "id": user["id"]},
        )
    update_session_key(username)
    return Response("Success.", 200)
