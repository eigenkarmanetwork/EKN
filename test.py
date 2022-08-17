from etn.database import DatabaseManager
from etn.helpers import get_votes, get_network, get_users_index
import time

with DatabaseManager() as db:
    result = db.execute("SELECT count(*) FROM users")
    total_users = result.fetchone()["count(*)"]
    result = db.execute("SELECT count(*) FROM votes")
    vote_rows = result.fetchone()["count(*)"]
    result = db.execute('SELECT sum("count") FROM votes')
    total_votes = result.fetchone()['sum("count")']
    print(f"{total_users=}")
    print(f"{vote_rows=}")
    print(f"{total_votes=}")

all = []
ts_all = []
caching_all = []
worst = 0.0
ts_best = 0.0
winner = (0, 0)
ts_winner = (0, 0)
input("Press enter to start. ")
test_start = time.monotonic()
print("Starting...")
try:
    for i in range(1, 1001):
        for ii in range(1, 1001):
            if i == ii:
                continue
            print(f"Calculating {ii} from the perspective of {i}. Caching...")
            start = time.monotonic()
            print(f"    {i} Caching... {start}")
            get_users_index(get_network(i), i)
            stop = time.monotonic()
            print(f"    {i} Caching Done {stop} ({stop - start})")
            if stop - start > 2: # If not previously cached.
                caching_all.append(stop - start)
            start = time.monotonic()
            print(f"    {ii} Caching... {start}")
            get_users_index(get_network(ii), ii)
            stop = time.monotonic()
            print(f"    {ii} Caching Done {stop} ({stop - start})")
            if stop - start > 2: # If not previously cached.
                caching_all.append(stop - start)
            print("Done caching.")
            start = time.monotonic()
            ts = get_votes(ii, i)
            stop = time.monotonic()
            length = stop - start
            all.append(length)
            if length >= worst:
                worst = length
                winner = (ii, i)
                print(f"New worst time: {length=} {winner=}")
            ts_all.append(ts)
            if ts >= ts_best:
                ts_best = ts
                ts_winner = (ii, i)
                print(f"New high score: {ts=} {ts_winner=}")
finally:
    test_stop = time.monotonic()
    print("Done!")
    print(f"Testing time: {test_start=} {test_stop=} ({test_stop - test_start})")
    print(f"Worst Time: {worst}, Involved: {winner}, Score {get_votes(winner[0], winner[1])}")
    print(f"Highest Trust: {ts_best}, Involved: {ts_winner}, Score {get_votes(ts_winner[0], ts_winner[1])}")
    print(f"Average Time: {sum(all) / len(all)}")
    print(f"Average Cache Time: {sum(caching_all) / len(caching_all)}")
    print(f"Average Trust: {sum(ts_all) / len(ts_all)}")
    print(f"{total_users=}")
    print(f"{vote_rows=}")
    print(f"{total_votes=}")
