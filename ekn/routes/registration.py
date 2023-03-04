from ekn.database import DatabaseManager
from ekn.decs import allow_cors
from ekn.helpers import get_params, verify_service, verify_credentials
from flask import Response
from typing import Optional
import hashlib
import json
import secrets
import time


@allow_cors
def register_user() -> Response:
    """Register a new user with the EKN
    Register a new user with the EKN, `username` and `password` must be passed
    in plain text. `username` is case sensitive and must not contain a colon (`:`).
    ---
    consumes:
    - application/json
    parameters:
    - in: body
      name: user
      description: The user to be registered.
      schema:
        type: object
        required:
          - username
          - password
        properties:
          username:
            type: string
            description: The new user's username. Is case sensitive and must not contain ':'
            example: mr_blobby
          password:
            type: string
            description: The raw password of the user.
            example: hunter2
    responses:
        200:
          description: Registration Successful
        409:
          description: Username is not available / Invalid Username / No password provided
    """
    username, password = get_params(["username", "password"])
    if not password:
        return Response("No password provided", 409)

    if not username or ":" in username:
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
            (db.ekn_service_id, username, id),
        )
    return Response("Registration Successful.", 200)


@allow_cors(hosts=["*"])
def register_temp_user() -> Response:
    """Register temporary user with the EKN
    Register a new temporary user with the EKN, `service_user` should be the username on the service
    you're registering a temp account for. `service_user` is case sensitive. Services must get
    permission from users before sending data off to EKN. This permission may be through ToS or otherwise.
    ---
    consumes:
    - application/json
    parameters:
    - in: body
      name: user
      description: The user to be registered.
      schema:
        type: object
        required:
          - service_user
          - service_name
          - service_key
        properties:
          service_user:
            type: string
            description: The case sensitive username on the service you're registering a temp account for.
            example: mr_blobby
          service_name:
            type: string
            description: The service's name
            example: Discord
          service_key:
            type: string
            description: The service's key in EKN
            example: a4b4da38aa385015769b44de37651a51
    responses:
        200:
          description: Registration Successful
        403:
          description: Service name or key is incorrect
        409:
          description: Username is not available
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
    """Register a new service with the EKN.
    `name` is case sensitive.  This will allow you to send
    votes on behalf of the users in your service.  Calling this function return's your service's
    EKN key.  For future requests, `name` should be passed as `service_name` and the string
    returned by this API call should be passed as `service_key`.
    ---
    consumes:
    - application/json
    parameters:
    - in: body
      name: service
      description: The service to be registered.
      schema:
        type: object
        required:
          - name
        properties:
          name:
            type: string
            description: The name of the service
            example: Discord
    responses:
        200:
          description: Registration Successful
          content:
            application/xml:
              schema:
                description: Service key
                type: string
                example: a4b4da38aa385015769b44de37651a51
        409:
          description: Name is not available
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
    """Registers a connection, or updates the connection if it already exists.
    Connects a user on a service to their user on EKN.
    `password_type` is optional, and defaults to `"raw_password"`.  This API call
    returns a JSON string that contains a key to authorize trust votes on behalf of
    the user.  However, if the user does not authorize services to vote on behalf of
    them, then a password hash is returned.  This feature is deprecated.  If a
    connection key is returned, then the user authorizes the service to cast votes on
    their behalf.  If a session key is returned, then the user authories the service
    to cast votes on their behalf so long as they've logged into EKN within the last
    24 hours. If a session key is returned, then the expires field will contain a unix
    timestamp of how long the session key is good for.  To get a new session key,
    please call `/get_current_key`.
    ---
    consumes:
    - application/json
    parameters:
    - in: body
      name: service
      description: User and service to be linked.
      schema:
        type: object
        required:
          - service_name
          - service_key
          - service_user
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
          service_user:
            type: string
            description: The username on the service
            example: discord_mr_blobby
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
          description: Registration Successful
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
                return Response("Service user already connected to the EKN.", 409)
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
