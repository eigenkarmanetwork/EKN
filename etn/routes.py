from etn.database import DatabaseManager
from etn.helpers import get_params, get_votes
from flask import Response
import hashlib
import json
import secrets


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


def vote() -> Response:
    """
    Message Structure:
    {
        "service_name": str (Service's name)
        "service_key": str (Service's key)
        "to": str (Username on Service)
        "from": str (Username on Service)
        "password": str (Password on ETN)
    }

    Returns:
    404: Service was not found.  # This will be returned if the name or key is incorrect.
    403: Username or Password is incorrect.  # For security reasons this will also be returned if to is not found or if they vote for themselves.
    200: Success.
    """
    service, key, to, _from, password = get_params(["service_name", "service_key", "to", "from", "password"])
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
        result = db.execute("SELECT * FROM connections WHERE service=:service_id AND service_user=:from",
                            {"service_id": service_obj["id"], "from": _from})
        from_service_user = result.fetchone()
        if not from_service_user:
            return Response("Username or Password is incorrect.", 403)
        result = db.execute("SELECT * FROM users WHERE id=:id", {"id": from_service_user["user"]})
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
        result = db.execute("SELECT * FROM connections WHERE service=:service_id AND service_user=:to",
                            {"service_id": service_obj["id"], "to": to})
        to_service_user = result.fetchone()
        if not to_service_user:
            return Response("Username or Password is incorrect.", 403)
        result = db.execute("SELECT * FROM users WHERE id=:id", {"id": to_service_user["user"]})
        to_user = result.fetchone()
        if not to_user:
            return Response("Username or Password is incorrect.", 403)
        from_user = user

        if from_user["id"] == to_user["id"]:
            return Response("Username or Password is incorrect.", 403)

        result = db.execute("SELECT * FROM votes WHERE user_from=:from AND user_to=:to",
                            {"from": from_user["id"], "to": to_user["id"]})
        current = result.fetchone()
        if current:
            db.execute("UPDATE votes SET count=:count WHERE user_from=:from AND user_to=:to",
                       {"from": from_user["id"], "to": to_user["id"], "count": current["count"] + 1})
        else:
            db.execute("INSERT INTO votes (user_from, user_to, count) VALUES (?, ?, 1)",
                       (from_user["id"], to_user["id"]))

    return Response("Success", 200)


def get_score() -> Response:
    """
    Message Structure:
    {
        "service_name": str (Service's name)
        "service_key": str (Service's key)
        "for": str (Username on Service)
        "from": str (Username on Service)
        "password": str (Password on ETN)
    }

    Returns:
    404: Service was not found.  # This will be returned if the name or key is incorrect.
    403: Username or Password is incorrect.  # For security reasons this will also be returned if for is not found or if they lookup themselves.
    200: JSON:
    {
        "for": str (Username Provided)
        "from": str (Username Provided)
        "score": float
    }
    """
    service, key, _for, _from, password = get_params(["service_name", "service_key", "for", "from", "password"])
    if _for == _from:
            return Response("Username or Password is incorrect.", 403)
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
        result = db.execute("SELECT * FROM connections WHERE service=:service_id AND service_user=:from",
                            {"service_id": service_obj["id"], "from": _from})
        from_service_user = result.fetchone()
        if not from_service_user:
            print("From user doesn't exist for service")
            return Response("Username or Password is incorrect.", 403)
        result = db.execute("SELECT * FROM users WHERE id=:id", {"id": from_service_user["user"]})
        user = result.fetchone()
        if not user:
            print("User doesn't exist in ETN")
            return Response("Username or Password is incorrect.", 403)
    salt = user["salt"]
    sha512 = hashlib.new("sha512")
    sha512.update(f"{password}:{salt}".encode("utf8"))
    password_hash = sha512.hexdigest()
    if password_hash != user["password"]:
        print("Password is incorrect")
        return Response("Username or Password is incorrect.", 403)
    with DatabaseManager() as db:
        result = db.execute("SELECT * FROM connections WHERE service=:service_id and service_user=:for",
                            {"service_id": service_obj["id"], "for": _for})
        for_service_user = result.fetchone()
        if not for_service_user:
            print("For user doesn't exist for service")
            return Response("Username or Password is incorrect.", 403)
        result = db.execute("SELECT * FROM users WHERE id=:id", {"id": for_service_user["user"]})
        for_user = result.fetchone()
        if not for_user:
            print("For user doesn't exist in ETN")
            return Response("Username or Password is incorrect.", 403)
    score = get_votes(for_user["id"], user["id"])
    response = {"for": _for, "from": _from, "score": score}
    return Response(json.dumps(response), 200)
