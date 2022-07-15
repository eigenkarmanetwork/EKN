from etn.database import DatabaseManager
from etn.decs import allow_cors
from etn.helpers import get_params
from flask import Response, request
import hashlib
import secrets


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
    200: Success.
    """

    if(request.method == "OPTIONS"):
        return Response()

    username, password = get_params(["username", "password"])

    salt = secrets.token_hex(6)
    sha512 = hashlib.new("sha512")
    sha512.update(f"{password}:{salt}".encode("utf8"))
    password_hash = sha512.hexdigest()
    with DatabaseManager() as db:
        result = db.execute("SELECT * FROM users WHERE username=:username", {"username": username})
        if result.fetchone():
            return Response("Username is not available.", 409)  # 409: Conflict
        db.execute("INSERT INTO users (username, password, salt) VALUES (?, ?, ?)", (username, password_hash, salt))
        result = db.execute("SELECT * FROM users WHERE username=:username", {"username": username})
        id = result.fetchone()["id"]
        db.execute("INSERT INTO connections (service, service_user, user) VALUES (?, ?, ?)", (db.etn_service_id, username, id))
    return Response("Registration Successful", 200)


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
        db.execute("INSERT INTO services (name, key, salt) VALUES (?, ?, ?)", (name, key_hash, salt))
        return Response(key, 200)


def register_connection() -> Response:
    """
    Message Structure:
    {
        "service_name": str (Service's name)
        "service_key": str (Service's key)
        "service_user": str (Username on Service)
        "username": str (Username on ETN)
        "password": str (Password on ETN)
    }

    Returns:
    404: Service was not found.  # This will be returned if the name or key is incorrect.
    403: Username or Password is incorrect.
    200: Success.
    """
    service, key, service_user, username, password = get_params(["service_name", "service_key", "service_user", "username", "password"])
    with DatabaseManager() as db:
        result = db.execute("SELECT * FROM services WHERE name=:name", {"name": service})
        service_obj = result.fetchone()
        if not service_obj:
            return Response("Service was not found.", 404)
        salt = service_obj["salt"]
        sha512 = hashlib.new("sha512")
        sha512.update(f"{key}:{salt}".encode("utf8"))
        key_hash = sha512.hexdigest()
        if key_hash != service_obj["key"]:
            return Response("Service was not found.", 404)
        result = db.execute("SELECT * FROM users WHERE username=:username", {"username": username})
        user = result.fetchone()
        if not user:
            return Response("Username or Password is incorrect.", 403)

    salt = user["salt"]
    sha512 = hashlib.new("sha512")
    sha512.update(f"{password}:{salt}".encode("utf8"))
    password_hash = sha512.hexdigest()
    if password_hash != user["password"]:
        return Response("Username or Password is incorrect.", 403)

    with DatabaseManager() as db:
        db.execute("INSERT INTO connections (service, service_user, user) VALUES (?, ?, ?)", (service_obj["id"], service_user, user["id"]))
    return Response("Connection Successful", 200)
