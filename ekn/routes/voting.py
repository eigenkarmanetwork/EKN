from ekn.database import DatabaseManager
from ekn.decs import allow_cors
from ekn.helpers import (
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
    """Allows a service to vote on behalf of a user
    `passwword_type` is optional and defaults to `"raw_password"`. `flavor` is optional and defaults to `"general"`. `amount` is optional and defaults to `1`.
    ---
    consumes:
    - application/json
    parameters:
    - in: body
      name: service
      description: Vote
      schema:
        type: object
        required:
          - service_name
          - service_key
          - to
          - from
          - password
          - password_type
        properties:
          service_name:
            type: string
            description: Service's name
            example: Discord
          service_key:
            type: string
            description: Service's key
            example: a4b4da38aa385015769b44de37651a51
          to:
            type: string
            description: Username on Service
            example: mr_blobby
          from:
            type: string
            description: Username on Service
            example: johnny
          password:
            type: string
            description: Password on EKN
            example: hunter2
          password_type:
            type: string
            description: The type of password
            enum: [raw_password, password_hash, connection_key, session_key]
            default: raw_password
          flavor:
            type: string
            default: general
          amount:
            type: number
            default: 1
    responses:
        200:
          description: Success
        400:
          description: User cannot vote for themselves / Cannot have a negative amount of trust
        403:
          description: Username or Password is incorrect / Service name or key is incorrect
        404:
          description: _to_ is not connected to this service / Flavor does not exist
    """
    service, key, to, for_, _from, password, password_type, flavor, amount = get_params(
        [
            "service_name",
            "service_key",
            "to",
            "for",
            "from",
            "password",
            "password_type",
            "flavor",
            "amount",
        ]
    )
    to = to or for_
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
    """Get how many times a user has voted for someone. This is NOT their trust score.
    Allows a service to get the number of times a user (A) has been trusted by user (B) on behalf of a
    user (B). `passwword_type` is optional and defaults to `"raw_password"`.

    If `flavor` is not specified, it will return the total number of times a user (B) has voted for a
    user (A) in *all* categories.
    ---
    consumes:
    - application/json
    parameters:
    - in: body
      name: service
      description: Vote
      schema:
        type: object
        required:
          - service_name
          - service_key
          - to
          - from
          - password
        properties:
          service_name:
            type: string
            description: Service's name
            example: Discord
          service_key:
            type: string
            description: Service's key
            example: a4b4da38aa385015769b44de37651a51
          to:
            type: string
            description: Username on Service
            example: mr_blobby
          from:
            type: string
            description: Username on Service
            example: johnny
          password:
            type: string
            description: Password on EKN
            example: hunter2
          password_type:
            type: string
            description: The type of password
            enum: [raw_password, password_hash, connection_key, session_key]
            default: raw_password
          flavor:
            type: string
            default: general
    responses:
      200:
        content:
          application/json:
            schema:
              type: object
              properties:
                for:
                  type: string
                  example: mr_blobby
                to:
                  type: string
                  example: mr_blobby_incognito
                votes:
                  type: integer
                  example: 42
                flavor:
                  type: string
                  example: general
      400:
        description: User cannot vote for themselves
      403:
        description: Username or Password is incorrect / Service name or key is incorrect
      404:
        description: _for_ is not connected to this service / Flavor does not exist
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
    """Allows a service to get the trust score for a user on behalf of, and from the perspective of another user.
    `password_type` is optional and defaults to `"raw_password"`. `flavor` is optional and defaults to `"general"`.
    ---
    consumes:
    - application/json
    parameters:
    - in: body
      name: service
      description: Vote
      schema:
        type: object
        required:
          - service_name
          - service_key
          - for
          - from
          - password
        properties:
          service_name:
            type: string
            description: Service's name
            example: Discord
          service_key:
            type: string
            description: Service's key
            example: a4b4da38aa385015769b44de37651a51
          for:
            type: string
            description: Username on Service
            example: mr_blobby
          from:
            type: string
            description: Username on Service
            example: mr_blobby_incognito
          password:
            type: string
            description: Password on EKN
            example: hunter2
          password_type:
            type: string
            description: The type of password
            enum: [raw_password, password_hash, connection_key, session_key]
            default: raw_password
          flavor:
            type: string
            default: general
    responses:
      200:
        content:
          application/json:
            schema:
              type: object
              properties:
                for:
                  type: string
                  example: mr_blobby
                from:
                  type: string
                  example: mr_blobby_incognito
                score:
                  type: number
                  example: 42.123
                flavor:
                  type: string
                  example: general
      400:
        description: User cannot view themselves
      403:
        description: Username or Password is incorrect / Service name or key is incorrect
      404:
        description: _for_ is not connected to this service / Flavor does not exist
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
    """Returns a JSON list of all the flavors available.
    ---
    responses:
        200:
          content:
            application/json:
              schema:
                type: array
                items:
                  type: string
                  example: category1
    """
    cats = []
    with DatabaseManager() as db:
        result = db.execute("SELECT * FROM categories")
        for row in result.fetchall():
            cats.append(row["category"])
    return Response(json.dumps(cats), 200)
