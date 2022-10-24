EKN Algorithm
=============

The code for the algorithm is in `/etn/helpers.py`.  This document will provide a near line by line breakdown of the code and what it does.

The algorthim's function is below and runs at O(n^3) where n is the number of people involved in calculation:

```py3
def get_votes(_for: int, _from: int, flavor: str) -> float:  # L80
```

The first step makes sure that the flavor you're looking for exists.  If it doesn't, then the trust is 0, so it returns 0.0.  Otherwise, it remembers the flavor's type and continues with the calculation.

```py3
with DatabaseManager() as db:
    result = db.execute("SELECT * FROM categories WHERE category=:flavor", {"flavor": flavor})
    row = result.fetchone()
    if not row:
        return 0.0
    flavor_type = row["type"]
```

Next, depending on the flavor's type, it will find all the nodes in the viewers trust graph/network.

```py3
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
```

Next, if the node being inspected is not in the trust network, then the trust for them is 0.0.  Otherwise, we remember the number of people in your network, and we build the index. The index is essentially just a conversion chart that tells us what user is what column/row in the matrix we're about to build.

```py3
if _for not in users_in_network:
    return 0.0
users_count = len(users_in_network)
users_index = get_users_index(users_in_network, _from)
```

Next, we build an empty matrix, and initiate some variables.

```py3
votes_matrix = np.zeros((users_count, users_count))
total_votes = 0
user_votes: dict[int, int] = {}
for user in users_in_network:
    user_votes[user] = 0
```

Next, we pull all the data we need from the database.  For each node in the network we wil perform a two part process.  In part 1, we find each node that has been trusted and how much it has been trusted and update our helper variables.  In part 2, we take that information and use it to update that column in the matrix.

```py3
with DatabaseManager() as db:
    for user in users_in_network:
        result = db.execute(f"SELECT * FROM votes {where_str} AND user_from=:from", {"from": user})
        total = 0
        votes: dict[int, int] = {}
        for v in result.fetchall():  # Part 1
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
        for vote in votes:  # Part 2
            if total == 0:
                break
            to_id_index = users_index[vote]
            votes_matrix[to_id_index, from_id_index] = votes[vote] / total
```

Next, we change the matrix so the node being inspected has no outgoing trust.  This in case the node tried to vote in any way to benifit themselves. This way those votes are disregarded.  Then it performs some other quick changes to matrix for calculation of the eigenvector.

```py3
for_index = users_index[_for]
for_user_votes = user_votes.get(_for, 0)
for i in range(users_count):
    votes_matrix[i][for_index] = 0
for i in range(1, users_count):
    votes_matrix[i, i] = -1
votes_matrix[0, 0] = 1
```

Now we calculate the actual eigenvector.

```py3
users_matrix = np.zeros(users_count)
users_matrix[0] = 1  # Viewer has 1 Trust

scores = list(np.linalg.solve(votes_matrix, users_matrix))
```

Next, we check if the flavor is a secondary flavor.  If it is, then we go through each node in the trust graph/network and see how many times they've voted for the node being inspected.  That number is then multiplied by the amount of trust we have for that user.  Otherwise, the score is just the result of the eigenvector calculation multiplied by the number of votes given by everyone in the trust graph/network minus the votes of the person being inspected.  Lastly, we make sure that the score is not -0.0 (which is possible due to how numpy works); if it is, we simply change it to 0.0.  We now have the result.

```py3
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
                s = round(scores[users_index[user]] * (total_votes - user_votes[user]), 2)

                # print(f"{user=} {s=}")
                score += row["count"] * s
    else:
        score = round(scores[for_index] * (total_votes - for_user_votes), 2)

    if score == -0.0:
        score = 0.0
    # print(score)
    return score
```
