from etn.database import DatabaseManager
from etn.decs import allow_cors
from etn.helpers import (
    get_params,
    get_votes,
    resolve_service_username,
    verify_credentials,
    verify_service,
    update_session_key,
)
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
        "flavor": Optional[str]
        "amount": Optional[int]
    }

    Returns:
    400: User cannot vote for themselves.
    400: Cannot have a negative amount of trust.
    403: Username or Password is incorrect.
    403: Service name or key is incorrect.
    404: 'to' is not connected to this service.
    404: Flavor does not exist.
    200: Success.
    """
    service, key, to, _from, password, password_type, flavor, amount = get_params(
        [
            "service_name",
            "service_key",
            "to",
            "from",
            "password",
            "password_type",
            "flavor",
            "amount",
        ]
    )
    amount = int(amount) if amount else 1

    if _from == to:
        return Response("User cannot vote for themselves.", 400)

    if not flavor:
        flavor = "general"
    else:
        with DatabaseManager() as db:
            result = db.execute(
                "SELECT * FROM categories WHERE category=:cat", {"cat": flavor}
            )
            if not result.fetchone():
                return Response("Flavor does not exist.", 404)

    service_obj = verify_service(service, key)
    if not service_obj:
        return Response("Service name or key is incorrect.", 403)
    from_user = verify_credentials(_from, password, password_type, service_obj["id"])
    if not from_user:
        return Response("Username or Password is incorrect.", 403)
    update_session_key(from_user["username"])
    to_user = resolve_service_username(service_obj["id"], to)
    if not to_user:
        return Response("'to' is not connected to this service.", 404)

    with DatabaseManager() as db:
        result = db.execute(
            "SELECT * FROM votes WHERE user_from=:from AND user_to=:to AND category=:cat",
            {"from": from_user["id"], "to": to_user["id"], "cat": flavor},
        )
        current = result.fetchone()
        if current:
            if (current["count"] + amount) < 0:
                return Response("Cannot have a negative amount of trust.", 400)
            db.execute(
                "UPDATE votes SET count=:count WHERE user_from=:from AND user_to=:to AND category=:cat",
                {
                    "from": from_user["id"],
                    "to": to_user["id"],
                    "count": current["count"] + amount,
                    "cat": flavor,
                },
            )
        else:
            if amount < 0:
                return Response("Cannot have a negative amount of trust.", 400)
            db.execute(
                "INSERT INTO votes (user_from, user_to, count, category) VALUES (?, ?, ?, ?)",
                (from_user["id"], to_user["id"], amount, flavor),
            )

    return Response("Success.", 200)


@allow_cors(hosts=["*"])
def get_vote_count() -> Response:
    """
    Get how many times a user has voted for someone. This is NOT their trust score.

    If flavor is not specified, it will return the total number of times a user has voted for someone in all categories.

    Message Structure:
    {
        "service_name": str (Service's name)
        "service_key": str (Service's key)
        "for": str (Username on Service)
        "from": str (Username on Service)
        "password": str (Password on ETN)
        "password_type": Optional[Literal["raw_password", "password_hash", "connection_key", "session_key"]]
        "flavor": Optional[str]
    }

    Returns:
    400: User cannot view themselves.
    403: Username or Password is incorrect.
    403: Service name or key is incorrect.
    404: 'for' is not connected to this service.
    404: Flavor does not exist.
    200: JSON:
    {
        "for": str (Username Provided)
        "from": str (Username Provided)
        "votes": int
        "flavor": str
    }
    """
    service, key, _for, _from, password, password_type, flavor = get_params(
        [
            "service_name",
            "service_key",
            "for",
            "from",
            "password",
            "password_type",
            "flavor",
        ]
    )

    if _from == _for:
        return Response("User cannot view themselves.", 400)

    flavor_str = ""
    if flavor:
        flavor_str = "AND category=:cat"
    if not flavor:
        flavor = "general"
    else:
        with DatabaseManager() as db:
            result = db.execute(
                "SELECT * FROM categories WHERE category=:cat", {"cat": flavor}
            )
            if not result.fetchone():
                return Response("Flavor does not exist.", 404)

    service_obj = verify_service(service, key)
    if not service_obj:
        return Response("Service name or key is incorrect.", 403)
    from_user = verify_credentials(_from, password, password_type, service_obj["id"])
    if not from_user:
        return Response("Username or Password is incorrect.", 403)
    update_session_key(from_user["username"])
    for_user = resolve_service_username(service_obj["id"], _for)
    if not for_user:
        return Response("'for' is not connected to this service.", 404)

    response = {"for": _for, "from": _from, "votes": 0, "flavor": flavor}
    with DatabaseManager() as db:
        result = db.execute(
            f'SELECT sum("count") AS "count" FROM votes WHERE user_from=:from AND user_to=:to {flavor_str}',
            {"from": from_user["id"], "to": for_user["id"], "cat": flavor},
        )
        current = result.fetchone()
        if current:
            if current["count"]:
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
        "flavor": Optional[str]
    }

    Returns:
    400: User cannot view themselves.
    403: Username or Password is incorrect.
    403: Service name or key is incorrect.
    404: 'for' is not connected to this service.
    404: Flavor does not exist.
    200: JSON:
    {
        "for": str (Username Provided)
        "from": str (Username Provided)
        "score": float
        "flavor": str
    }
    """
    service, key, _for, _from, password, password_type, flavor = get_params(
        [
            "service_name",
            "service_key",
            "for",
            "from",
            "password",
            "password_type",
            "flavor",
        ]
    )
    if _for == _from:
        return Response("User cannot view themselves.", 400)

    if not flavor:
        flavor = "general"
    else:
        with DatabaseManager() as db:
            result = db.execute(
                "SELECT * FROM categories WHERE category=:cat", {"cat": flavor}
            )
            if not result.fetchone():
                return Response("Flavor does not exist.", 404)

    service_obj = verify_service(service, key)
    if not service_obj:
        return Response("Service name or key is incorrect.", 403)
    from_user = verify_credentials(_from, password, password_type, service_obj["id"])
    if not from_user:
        return Response("Username or Password is incorrect.", 403)
    update_session_key(from_user["username"])
    for_user = resolve_service_username(service_obj["id"], _for)
    if not for_user:
        return Response("'for' is not connected to this service.", 404)

    score = get_votes(for_user["id"], from_user["id"], flavor)
    response = {"for": _for, "from": _from, "score": score, "flavor": flavor}
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
