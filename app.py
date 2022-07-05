from etn.database import DatabaseManager
from flask import Flask, Response, request
from typing import Any
import hashlib
import secrets

app = Flask(__name__)


def get_params(params: list[str]) -> Any:
    ret = []
    if request.is_json:
        message = request.get_json()
        assert isinstance(message, dict)
        for param in params:
            if param in params:
                ret.append(message[param])
            else:
                ret.append(None)
    else:
        for param in params:
            ret.append(request.form.get(param, None))
    if len(ret) == 1:
        return ret[0]
    elif len(ret) == 0:
        return None
    return ret

@app.route("/register_user", methods=["POST"])
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


@app.route("/register_service", methods=["POST"])
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
        while True:
            key = secrets.token_hex(16)
            result = db.execute("SELECT * FROM services WHERE key=:key", {"key": key})
            if result.fetchone() is None:
                break
        db.execute("INSERT INTO services (key, name) VALUES (?, ?)", (key, name))
        return Response(key, 200)


@app.route("/register_connection", methods=["POST"])
def register_connection() -> Response:
    """
    Message Structure:
    {
        "service": str (Service's key)
        "service_user": str (Username on Service)
        "username": str (Username on ETN)
        "password": str (Password on ETN)
    }

    Returns:
    404: Service was not found.
    403: Username or Password is incorrect.
    200: Success.
    """
    key, service_user, username, password = get_params(["service", "service_user", "username", "password"])
    with DatabaseManager() as db:
        result = db.execute("SELECT * FROM services WHERE key=:key", {"key": key})
        service = result.fetchone()
        if not service:
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
        db.execute("INSERT INTO connections (service, service_user, user) VALUES (?, ?, ?)", (service["id"], service_user, user["id"]))
    return Response("Connection Successful", 200)


@app.route("/vote", methods=["POST"])
def vote() -> Response:
    """
    Message Structure:
    {
        "service": str (Service's key)
        "to": str (Username on Service)
        "from": str (Username on Service)
        "password": str (Password on ETN)
    }

    Returns:
    404: Service was not found.
    403: Username or Password is incorrect.  # For security reasons this will also be returned if to is not found or if they vote for themselves.
    200: Success.
    """
    key, to, _from, password = get_params(["service", "to", "from", "password"])
    with DatabaseManager() as db:
        result = db.execute("SELECT * FROM services WHERE key=:key", {"key": key})
        service = result.fetchone()
        if not service:
            return Response("Service was not found.", 404)
        result = db.execute("SELECT * FROM connections WHERE service=:service_id AND service_user=:from",
                            {"service_id": service["id"], "from": _from})
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
                            {"service_id": service["id"], "to": to})
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
