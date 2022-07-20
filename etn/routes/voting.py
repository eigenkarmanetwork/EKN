from etn.database import DatabaseManager
from etn.decs import allow_cors
from etn.helpers import get_params, get_votes, resolve_service_username, verify_credentials, verify_service
from flask import Response, request
import hashlib
import json


@allow_cors(hosts=["*"])
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
    400: User cannot vote for themselves.
    403: Username or Password is incorrect.
    403: Service name or key is incorrect.
    404: 'to' is not connected to this service.
    200: Success.
    """
    service, key, to, _from, password = get_params(["service_name", "service_key", "to", "from", "password"])

    if _from == to:
        return Response("User cannot vote for themselves.", 400)

    service_obj = verify_service(service, key)
    if not service_obj:
        return Response("Service name or key is incorrect.", 403)
    user = resolve_service_username(service_obj["id"], _from)
    if not user:
        return Response("Username or Password is incorrect.", 403)
    from_user = verify_credentials(user["username"], password)
    if not from_user:
        return Response("Username or Password is incorrect.", 403)
    to_user = resolve_service_username(service_obj["id"], to)
    if not to_user:
        return Response("'to' is not connected to this service.", 404)

    with DatabaseManager() as db:
        result = db.execute(
            "SELECT * FROM votes WHERE user_from=:from AND user_to=:to",
            {"from": from_user["id"], "to": to_user["id"]},
        )
        current = result.fetchone()
        if current:
            db.execute(
                "UPDATE votes SET count=:count WHERE user_from=:from AND user_to=:to",
                {"from": from_user["id"], "to": to_user["id"], "count": current["count"] + 1},
            )
        else:
            db.execute(
                "INSERT INTO votes (user_from, user_to, count) VALUES (?, ?, 1)",
                (from_user["id"], to_user["id"]),
            )

    return Response("Success", 200)


@allow_cors(hosts=["*"])
def get_vote_count() -> Response:
    """
    Get how many times a user has voted for someone. This is NOT their trust score.

    Message Structure:
    {
        "service_name": str (Service's name)
        "service_key": str (Service's key)
        "for": str (Username on Service)
        "from": str (Username on Service)
        "password": str (Password on ETN)
    }

    Returns:
    400: User cannot view themselves.
    403: Username or Password is incorrect.
    403: Service name or key is incorrect.
    404: 'for' is not connected to this service.
    200: JSON:
    {
        "for": str (Username Provided)
        "from": str (Username Provided)
        "votes": int
    }
    """
    service, key, _for, _from, password = get_params(
        ["service_name", "service_key", "for", "from", "password"]
    )

    if _from == _for:
        return Response("User cannot view themselves.", 400)

    service_obj = verify_service(service, key)
    if not service_obj:
        return Response("Service name or key is incorrect.", 403)
    user = resolve_service_username(service_obj["id"], _from)
    if not user:
        return Response("Username or Password is incorrect.", 403)
    from_user = verify_credentials(user["username"], password)
    if not from_user:
        return Response("Username or Password is incorrect.", 403)
    for_user = resolve_service_username(service_obj["id"], _for)
    if not for_user:
        return Response("'for' is not connected to this service.", 404)

    response = {"for": _for, "from": _from, "votes": 0}
    with DatabaseManager() as db:
        result = db.execute(
            "SELECT * FROM votes WHERE user_from=:from AND user_to=:to",
            {"from": from_user["id"], "to": for_user["id"]},
        )
        current = result.fetchone()
        if current:
            response["votes"] = current["count"]

    return Response(json.dumps(response), 200)


@allow_cors(hosts=["*"])
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
    service, key, _for, _from, password = get_params(
        ["service_name", "service_key", "for", "from", "password"]
    )
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
        result = db.execute(
            "SELECT * FROM connections WHERE service=:service_id AND service_user=:from",
            {"service_id": service_obj["id"], "from": _from},
        )
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
        result = db.execute(
            "SELECT * FROM connections WHERE service=:service_id and service_user=:for",
            {"service_id": service_obj["id"], "for": _for},
        )
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
