from etn.database import DatabaseManager
from etn.types import PASSWORD_TYPE
from flask import request
from typing import Any, Optional
import numpy as np
import hashlib
import json
import secrets
import sqlite3
import time


NETWORK_SIZE_LIMIT = 10_000


def get_params(params: list[str]) -> Any:
    ret = []
    if request.is_json:
        message = request.get_json()
        assert isinstance(message, dict)
        for param in params:
            if param in message:
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


def get_where_str(flavors: Optional[list[str]]) -> str:
    if not flavors:
        where_str = "WHERE '1'='1'"
    else:
        where_str = "WHERE category in ("
        for flavor in flavors:
            where_str += f"'{flavor}', "
        where_str = where_str.strip(", ")  # Strip tailing comma
        where_str += ")"
    return where_str


def get_network(
    user: int, flavors: Optional[list[str]] = None, checking: Optional[int] = None
) -> set[int]:
    """
    Function runs at O(n^2) time.
    """
    where_str = get_where_str(flavors)
    users: set[int] = {user}
    to_process: set[int] = {user}
    with DatabaseManager() as db:
        while len(to_process) > 0 and len(users) < NETWORK_SIZE_LIMIT:
            u = to_process.pop()
            if u == checking:
                continue
            result = db.execute(
                f"SELECT * FROM votes {where_str} AND user_from=:user", {"user": u}
            )
            for uu in result.fetchall():
                if uu["user_to"] not in users:
                    users.add(uu["user_to"])
                    to_process.add(uu["user_to"])
    return users


def get_users_index(users: set[int], from_user: int) -> dict[int, int]:
    """
    Function runs at O(n^2) time.
    """
    users = users.copy()
    users.remove(from_user)
    indexs = {from_user: 0}
    for i, user in enumerate(users):
        indexs[user] = i + 1
    return indexs


def get_votes(_for: int, _from: int, flavor: str) -> float:
    """
    np.lingalg.solve calls LAPACK gesv which runs at O(n^3) time.
    """

    with DatabaseManager() as db:
        result = db.execute(
            "SELECT * FROM categories WHERE category=:flavor", {"flavor": flavor}
        )
        row = result.fetchone()
        if not row:
            return 0.0
        flavor_type = row["type"]

    if flavor_type == "general":
        users_in_network = get_network(_from, checking=_for)
        where_str = "WHERE '1'='1'"
    elif flavor_type == "normal":
        users_in_network = get_network(_from, [flavor], _for)
        where_str = get_where_str([flavor])
    elif flavor_type == "secondary":
        users_in_network = get_network(_from, [row["secondary_of"]], _for)
        where_str = get_where_str([row["secondary_of"]])
    elif flavor_type == "composite":
        flavors = json.loads(row["composite_of"])
        flavors.append(flavor)
        users_in_network = get_network(_from, flavors, _for)
        where_str = get_where_str(flavors)

    if _for not in users_in_network:
        return 0.0
    users_count = len(users_in_network)
    users_index = get_users_index(users_in_network, _from)

    votes_matrix = np.zeros((users_count, users_count))
    total_votes = 0
    user_votes: dict[int, int] = {}
    for user in users_in_network:
        user_votes[user] = 0
    with DatabaseManager() as db:
        for user in users_in_network:
            if user == _for:
                continue
            result = db.execute(
                f"SELECT * FROM votes {where_str} AND user_from=:from", {"from": user}
            )
            total = 0
            votes: dict[int, int] = {}
            for v in result.fetchall():
                if v["user_to"] in votes:
                    votes[v["user_to"]] += v["count"]
                else:
                    votes[v["user_to"]] = v["count"]
                total += v["count"]
                total_votes += v["count"]
                if v["user_from"] in user_votes:
                    user_votes[v["user_from"]] += v["count"]
                else:
                    user_votes[v["user_from"]] = v["count"]
            from_id_index = users_index[user]
            for vote in votes:
                if total == 0:
                    break
                to_id_index = users_index[vote]
                # print(f"Votes: {vote=} {votes[vote]=} / {total=}")
                votes_matrix[to_id_index, from_id_index] = votes[vote] / total
    for_index = users_index[_for]
    for_user_votes = user_votes.get(_for, 0)
    for i in range(users_count):
        votes_matrix[i][for_index] = 0
    for i in range(1, users_count):
        votes_matrix[i, i] = 0
    # print("User Index:")
    # print(users_index)
    # print("Votes Matrix:")
    # print(votes_matrix.T[0])

    scores = np.zeros(users_count)
    scores[0] = 1  # Viewer has 100% Trust

    decay = 0.25
    solved = False
    for _ in range(1000):  # Only do 1000 rounds
        old_score = scores
        scores = np.dot(votes_matrix, scores) * decay
        scores[0] = 1  # Viewer will always have 100% Trust

        # Check if solved
        solved = True
        for a, b in zip(old_score, scores):
            if not round(a, 8) == round(b, 8):
                solved = False
                break
        if solved:
            break
    # print("Scores:")
    # print(scores)
    # print("Total Votes:")
    # print(total_votes - for_user_votes)
    # print("Score: ")

    if flavor_type == "secondary":
        score = round(scores[for_index] * (total_votes - for_user_votes), 2)
        with DatabaseManager() as db:
            for user in users_index:
                result = db.execute(
                    "SELECT * FROM votes WHERE category=:cat AND user_from=:from AND user_to=:for",
                    {"cat": flavor, "from": user, "for": _for},
                )
                row = result.fetchone()
                if not row:
                    # print(f"Not row for {user}")
                    continue
                if user == _from:
                    # print("Direct add")
                    score += row["count"]
                    continue
                # print(f"{scores=}")
                # print(f"{user_votes=}")
                s = round(
                    scores[users_index[user]] * (total_votes - user_votes[user]), 2
                )

                # print(f"{user=} {s=}")
                score += row["count"] * s
    else:
        score = round(scores[for_index] * (total_votes - for_user_votes), 2)

    if score == -0.0:
        score = 0.0
    # print(score)
    return score


def verify_credentials(
    username: str,
    password: str,
    password_type: PASSWORD_TYPE = None,
    service_id: Optional[int] = None,
) -> Optional[sqlite3.Row]:
    """
    Verifies an ETN username and password/key.
    """

    if service_id and password_type != "connection_key":
        user = resolve_service_username(service_id, username)
        if user:
            username = user["username"]
    if password_type is None or password_type == "raw_password":
        return verify_credentials_raw(username, password)
    elif password_type == "password_hash":
        return verify_credentials_hash(username, password)
    elif password_type == "connection_key":
        if not service_id:
            return None
        return verify_service_username(service_id, username, password)
    elif password_type == "session_key":
        return verify_session_key(username, password)
    else:
        return None


def verify_credentials_raw(username: str, password: str) -> Optional[sqlite3.Row]:
    """
    Verifies an ETN username and raw password.
    """

    with DatabaseManager() as db:
        result = db.execute(
            "SELECT * FROM users WHERE username=:username", {"username": username}
        )
        user = result.fetchone()
        if not user:
            return None

        salt = user["salt"]
        sha512 = hashlib.new("sha512")
        sha512.update(f"{password}:{salt}".encode("utf8"))
        password_hash = sha512.hexdigest()
        if not password_hash == user["password"]:
            return None
        return user


def verify_credentials_hash(username: str, password_hash: str) -> Optional[sqlite3.Row]:
    """
    Verifies an ETN username and password hash.
    """

    with DatabaseManager() as db:
        result = db.execute(
            "SELECT * FROM users WHERE username=:username", {"username": username}
        )
        user = result.fetchone()
        if not user:
            return None

        if not password_hash == user["password"]:
            return None
        return user


def verify_session_key(username: str, key: str) -> Optional[sqlite3.Row]:
    """
    Verifies an ETN user id and session key.
    """

    with DatabaseManager() as db:
        result = db.execute(
            "SELECT * FROM users WHERE username=:username", {"username": username}
        )
        user = result.fetchone()
        if not user:
            return None
        if user["security"] == 2:
            return None
        result = db.execute(
            "SELECT * FROM session_keys WHERE user=:user_id", {"user_id": user["id"]}
        )
        row = result.fetchone()
        if not row:
            return None
        if row["expires"] < int(time.time()):
            return None

        if key != row["key"]:
            return None
        return user


def verify_service(service: str, key: str) -> Optional[sqlite3.Row]:
    """
    Verifies a service's credentials.
    """

    with DatabaseManager() as db:
        result = db.execute(
            "SELECT * FROM services WHERE name=:name", {"name": service}
        )
        service_obj = result.fetchone()
        if not service_obj:
            return None
        salt = service_obj["salt"]
        sha512 = hashlib.new("sha512")
        sha512.update(f"{key}:{salt}".encode("utf8"))
        key_hash = sha512.hexdigest()
        if key_hash != service_obj["key"]:
            return None
        return service_obj


def resolve_service_username(
    service_id: int, service_user: str
) -> Optional[sqlite3.Row]:
    """
    Gets an ETN username from a service id and the username on the service.
    """

    with DatabaseManager() as db:
        result = db.execute(
            "SELECT * FROM connections WHERE service=:service_id AND service_user=:service_user",
            {"service_id": service_id, "service_user": service_user},
        )
        service_user_obj = result.fetchone()
        if not service_user_obj:
            return None
        result = db.execute(
            "SELECT * FROM users WHERE id=:id", {"id": service_user_obj["user"]}
        )
        user = result.fetchone()
        if not user:
            return None
        return user


def verify_service_username(
    service_id: int, service_user: str, key: str
) -> Optional[sqlite3.Row]:
    """
    Gets an ETN username from a service id and the username on the service.
    """

    with DatabaseManager() as db:
        result = db.execute(
            "SELECT * FROM connections WHERE service=:service_id AND service_user=:service_user",
            {"service_id": service_id, "service_user": service_user},
        )
        service_user_obj = result.fetchone()
        if not service_user_obj:
            return None
        if service_user_obj["key"] is None or service_user_obj["key"] != key:
            return None
        result = db.execute(
            "SELECT * FROM users WHERE id=:id", {"id": service_user_obj["user"]}
        )
        user = result.fetchone()
        if not user:
            return None
        if user["security"] != 0:
            return None
        return user


def update_session_key(username: str) -> None:
    """
    Updates a user's session key if neccessary.
    """
    with DatabaseManager() as db:
        result = db.execute(
            "SELECT * FROM users WHERE username=:username", {"username": username}
        )
        user = result.fetchone()
        assert user is not None
        if user["security"] == 2:
            return
        result = db.execute(
            "SELECT * FROM session_keys WHERE user=:user_id", {"user_id": user["id"]}
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
