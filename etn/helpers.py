from etn.database import DatabaseManager
from flask import request
from typing import Any, Optional
import numpy as np
import hashlib
import sqlite3


NETWORK_SIZE_LIMIT = 10_000


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


def get_network(user: int) -> list[int]:
    users: list[int] = [user]
    to_process: list[int] = [user]
    with DatabaseManager() as db:
        while len(to_process) > 0 and len(users) < NETWORK_SIZE_LIMIT:
            u = to_process.pop()
            result = db.execute("SELECT * FROM votes WHERE user_from=:user", {"user": u})
            for uu in result.fetchall():
                if uu["user_to"] not in users:
                    users.append(uu["user_to"])
                    to_process.append(uu["user_to"])
    return users


def get_users_index(users: list[int], from_user: int) -> dict[int, int]:
    users = users.copy()
    users.pop(users.index(from_user))
    ids = sorted(list(users))
    indexs = {from_user: 0}
    for id in ids:
        indexs[id] = ids.index(id) + 1
    return indexs


def get_votes(_for: int, _from: int) -> float:
    users_in_network = get_network(_from)
    if _for not in users_in_network:
        return 0.0
    users_count = len(users_in_network)
    users_index = get_users_index(users_in_network, _from)

    votes_matrix = np.zeros((users_count, users_count))
    total_votes = 0
    for_user_votes = 0
    with DatabaseManager() as db:
        for user in users_in_network:
            result = db.execute("SELECT * FROM votes WHERE user_from=:from", {"from": user})
            total = 0
            votes = {}
            for v in result.fetchall():
                votes[v["user_to"]] = v["count"]
                total += v["count"]
                total_votes += v["count"]
                if v["user_from"] == _for:
                    for_user_votes += v["count"]
            from_id_index = users_index[user]
            for vote in votes:
                to_id_index = users_index[vote]
                votes_matrix[to_id_index, from_id_index] = votes[vote] / total
    for_index = users_index[_for]
    for i in range(users_count):
        votes_matrix[i][for_index] = 0
    for i in range(1, users_count):
        votes_matrix[i, i] = -1
    votes_matrix[0, 0] = 1
    print("User Index:")
    print(users_index)
    print("Votes Matrix:")
    print(votes_matrix)

    users_matrix = np.zeros(users_count)
    users_matrix[0] = 1  # Viewer has 1 Trust
    print("Users Matrix:")
    print(users_matrix)

    scores = list(np.linalg.solve(votes_matrix, users_matrix))
    print("Scores:")
    print(scores)
    print("Total Votes:")
    print(total_votes - for_user_votes)
    print("Score: ")
    score = round(scores[for_index] * (total_votes - for_user_votes), 2)
    if score == -0.0:
        score = 0.0
    print(score)
    return score


def verify_credentials(username: str, password: str) -> Optional[sqlite3.Row]:
    """
    Verifies an ETN username and password.
    """

    with DatabaseManager() as db:
        result = db.execute("SELECT * FROM users WHERE username=:username", {"username": username})
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
        result = db.execute("SELECT * FROM users WHERE username=:username", {"username": username})
        user = result.fetchone()
        if not user:
            return None

        if not password_hash == user["password"]:
            return None
        return user


def verify_service(service: str, key: str) -> Optional[sqlite3.Row]:
    """
    Verifies a service's credentials.
    """

    with DatabaseManager() as db:
        result = db.execute("SELECT * FROM services WHERE name=:name", {"name": service})
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


def resolve_service_username(service_id: int, service_user: str) -> Optional[sqlite3.Row]:
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
        result = db.execute("SELECT * FROM users WHERE id=:id", {"id": service_user_obj["user"]})
        user = result.fetchone()
        if not user:
            return None
        return user
