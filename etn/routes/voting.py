from etn.database import DatabaseManager
from etn.decs import allow_cors
from etn.helpers import get_params, get_votes, resolve_service_username, verify_credentials, verify_service
from flask import Response
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
        "password_type": Optional[Literal["raw_password", "password_hash", "connection_key", "session_key"]]
        "amount": Optional[int]
    }

    Returns:
    400: User cannot vote for themselves.
    400: Cannot have a negative amount of trust.
    403: Username or Password is incorrect.
    403: Service name or key is incorrect.
    404: 'to' is not connected to this service.
    200: Success.
    """
    service, key, to, _from, password, password_type, amount = get_params(
        ["service_name", "service_key", "to", "from", "password", "password_type", "amount"]
    )
    amount = int(amount) if amount else 1

    if _from == to:
        return Response("User cannot vote for themselves.", 400)

    service_obj = verify_service(service, key)
    if not service_obj:
        return Response("Service name or key is incorrect.", 403)
    from_user = verify_credentials(_from, password, password_type, service_obj["id"])
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
            if (current["count"] + amount) < 0:
                return Response("Cannot have a negative amount of trust.", 400)
            db.execute(
                "UPDATE votes SET count=:count WHERE user_from=:from AND user_to=:to",
                {"from": from_user["id"], "to": to_user["id"], "count": current["count"] + amount},
            )
        else:
            if amount < 0:
                return Response("Cannot have a negative amount of trust.", 400)
            db.execute(
                "INSERT INTO votes (user_from, user_to, count) VALUES (?, ?, ?)",
                (from_user["id"], to_user["id"], amount),
            )

    return Response("Success.", 200)


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
        "password_type": Optional[Literal["raw_password", "password_hash", "connection_key", "session_key"]]
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
    service, key, _for, _from, password, password_type = get_params(
        ["service_name", "service_key", "for", "from", "password", "password_type"]
    )

    if _from == _for:
        return Response("User cannot view themselves.", 400)

    service_obj = verify_service(service, key)
    if not service_obj:
        return Response("Service name or key is incorrect.", 403)
    user = resolve_service_username(service_obj["id"], _from)
    if not user:
        return Response("Username or Password is incorrect.", 403)
    from_user = verify_credentials(user["username"], password, password_type, service_obj["id"])
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
        "password_type": Optional[Literal["raw_password", "password_hash", "connection_key", "session_key"]]
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
        "score": float
    }
    """
    service, key, _for, _from, password, password_type = get_params(
        ["service_name", "service_key", "for", "from", "password", "password_type"]
    )
    if _for == _from:
        return Response("User cannot view themselves.", 400)

    service_obj = verify_service(service, key)
    if not service_obj:
        return Response("Service name or key is incorrect.", 403)
    user = resolve_service_username(service_obj["id"], _from)
    if not user:
        return Response("Username or Password is incorrect.", 403)
    from_user = verify_credentials(user["username"], password, password_type, service_obj["id"])
    if not from_user:
        return Response("Username or Password is incorrect.", 403)
    for_user = resolve_service_username(service_obj["id"], _for)
    if not for_user:
        return Response("'for' is not connected to this service.", 404)

    score = get_votes(for_user["id"], from_user["id"])
    response = {"for": _for, "from": _from, "score": score}
    return Response(json.dumps(response), 200)

@allow_cors(hosts=["*"])
def categories() -> Response:
    """
    GET /categories

    Returns:
    200: JSON list of all categories
    """
    cats = []
    with DatabaseManager() as db:
        result = db.execute("SELECT * FROM categories")
        for row in result.fetchall():
            cats.append(row["category"])
    return Response(json.dumps(cats), 200)
