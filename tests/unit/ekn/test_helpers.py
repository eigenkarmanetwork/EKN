import pytest
from unittest.mock import MagicMock, patch

from ekn.helpers import (
    get_params, get_where_str, get_users_index, get_network,
    get_votes, DECAY
)


@pytest.mark.parametrize('data, expected', (
    ({'param1': 1, 'param2': 2}, [1, 2, None]),
    ({'param1': 1, 'param2': 2, 'param3': 3}, [1, 2, 3]),
    ({'param1': 1, 'param2': 2, 'bla': 234, 'ble': 13}, [1, 2, None]),

    ({'bla': 234, 'ble': 13}, [None, None, None]),
    ({}, [None, None, None]),
))
def test_get_params_json(data, expected):
    request = MagicMock(is_json=True)
    request.get_json.return_value = data
    with patch('ekn.helpers.request', request):
        assert get_params(['param1', 'param2', 'param3']) == expected


@pytest.mark.parametrize('data, expected', (
    ({'param1': 1, 'param2': 2}, [1, 2, None]),
    ({'param1': 1, 'param2': 2, 'param3': 3}, [1, 2, 3]),
    ({'param1': 1, 'param2': 2, 'bla': 234, 'ble': 13}, [1, 2, None]),

    ({'bla': 234, 'ble': 13}, [None, None, None]),
    ({}, [None, None, None]),
))
def test_get_params_body(data, expected):
    request = MagicMock(is_json=False, form=data)
    with patch('ekn.helpers.request', request):
        assert get_params(['param1', 'param2', 'param3']) == expected


@pytest.mark.parametrize('data, expected', (
    ({'param1': 1}, 1),
    ({'param3': 3}, None),
    ({}, None),
))
def test_get_params_single(data, expected):
    request = MagicMock(is_json=False, form=data)
    with patch('ekn.helpers.request', request):
        assert get_params(['param1']) == expected


def test_get_params_empty():
    request = MagicMock(is_json=False, form={'bla': 'bla'})
    with patch('ekn.helpers.request', request):
        assert get_params([]) is None


@pytest.mark.parametrize('flavors', (None, [], {}))
def test_get_where_str_empty(flavors):
    assert get_where_str(flavors) == "WHERE '1'='1'"


@pytest.mark.parametrize('flavors, expected', (
    (['a'], "'a'"),
    (['a', 'b', 'c'], "'a', 'b', 'c'"),
    (['bla', 'ble'], "'bla', 'ble'"),
))
def test_get_where_str(flavors, expected):
    assert get_where_str(flavors) == f'WHERE category in ({expected})'


@pytest.mark.parametrize('users, expected', (
    ({4, 2, 1, 3}, {1: 1, 2: 2, 3: 0, 4: 3}),
    ({1, 2, 3, 4}, {1: 1, 2: 2, 3: 0, 4: 3}),
))
def test_get_users_index(users, expected):
    length = len(users)
    assert get_users_index(users, 3) == expected
    # Make sure the original set is untouched
    assert len(users) == length


def test_get_users_index_empty():
    with pytest.raises(KeyError, match="3"):
        assert get_users_index(set(), 3)


def test_get_users_index_missing():
    with pytest.raises(KeyError, match="42"):
        assert get_users_index({1, 2, 3, 4}, 42)


def test_get_network_empty(db):
    # The network always contains the checked item
    assert get_network(1, "WHERE 1=1") == {1}


def test_get_network(make_network):
    votes = [
        # Direct contacts
        (1, 2), (1, 3), (1, 4), (1, 5),
        # Second level
        (2, 1), (2, 3), (2, 6),
        (3, 7),
        (4, 1), (4, 2),
        # Third level
        (6, 1), (6, 3),
        (7, 8), (7, 9),
    ]
    make_network(votes)
    assert get_network(1, "WHERE 1=1") == set(range(1, 10))


def test_get_network_sparse(make_network):
    votes = [
        # Direct contacts
        (1, 2), (1, 5),
        # Second level
        (2, 1), (2, 6), (3, 7),
        (4, 1), (4, 2),
        # Third level
        (6, 1),
        (7, 8), (7, 9),
    ]
    make_network(votes)
    assert get_network(1, "WHERE 1=1") == {1, 2, 5, 6}


def test_get_network_cycle(make_network):
    votes = [(1, 2), (2, 3), (3, 4), (4, 5), (5, 1)]
    make_network(votes)
    assert get_network(1, "WHERE 1=1") == {1, 2, 3, 4, 5}


## Base tests to handle no connection between 2 users
def test_get_votes_empty_db(db):
    assert get_votes(1, 2, 'general') == 0.0


@pytest.mark.parametrize('flavor', ('bla bla bla', 'normal', 'secondary', 'composite'))
def test_get_votes_different_flavor(network, flavor):
    assert get_votes(1, 2, flavor) == 0.0


def test_get_votes_no_connection_from(network):
    assert get_votes(1, 200, 'general') == 0.0


def test_get_votes_no_connection_to(network):
    assert get_votes(200, 2, 'general') == 0.0


## Tests that calculate votes
def test_get_votes_basic(make_network):
    # The basic case where there are only 2 users, and one of them has voted a few times for the other
    make_network([(2, 1, 5)])
    assert get_votes(1, 2, 'general') == 5 * (1 - DECAY)
    assert get_votes(2, 1, 'general') == 0.0


def test_get_votes_mutual(make_network):
    # there are only 2 users, both of which have voted for each other
    make_network([(2, 1, 5), (1, 2, 4)])
    assert get_votes(1, 2, 'general') == 5 * (1 - DECAY)
    assert get_votes(2, 1, 'general') == 4 * (1 - DECAY)


@pytest.mark.parametrize('votes', (
    # Basic case where each person in the chain has received 1 vote
    [(2, 1, 1), (3, 2, 1), (4, 3, 1), (5, 4, 1), (6, 5, 1)],

    # Each person received more than 1 vote, but they all vote the same
    [(2, 1, 2), (3, 2, 2), (4, 3, 2), (5, 4, 2), (6, 5, 2)],
    [(2, 1, 3), (3, 2, 3), (4, 3, 3), (5, 4, 3), (6, 5, 3)],

    # Different people vote different amounts
    [(2, 1, 1), (3, 2, 2), (4, 3, 3), (5, 4, 4), (6, 5, 5)],
    [(2, 1, 10), (3, 2, 1), (4, 3, 20), (5, 4, 1), (6, 5, 50)],
))
def test_get_votes_long_chain(make_network, votes):
    # the users are connected via a longish chain of votes
    #
    # user 1 --- user 2 --- user 3 --- user 4 --- user 5 --- user 6
    make_network(votes)
    for i in range(1, 6):
        score = (1 - DECAY) ** i
        total_votes = sum(vote for _, _, vote in reversed(votes[:i]))
        assert get_votes(1, i + 1, 'general') == pytest.approx(score * total_votes, 0.1)


@pytest.mark.parametrize('votes', (
    # Seeing as the from and for nodes are directly connected, only the
    # votes from user 1 to user 2 are considered
    [1, 1, 1, 1],
    [1, 1, 2, 1],
    [1, 4, 1, 5],

    # The score gets scaled by the amount of votes given
    [12, 1, 1, 1],
    [13, 1, -1, 1],
    [14, 20, 1, 10000],
))
def test_get_votes_when_1_to_n(make_network, votes):
    # User 1 has voted for a lot of other users
    #
    #           /--- user 2
    #          /---- user 3
    #  user 1 <----- user 4
    #          \---- user 5
    #
    u1_u2, u1_u3, u1_u4, u1_u5 = votes
    graph = [
        (2, 1, u1_u2), (3, 1, u1_u3),
        (4, 1, u1_u4), (5, 1, u1_u5),
    ]

    make_network(graph)
    score = (1 - DECAY) * votes[0]
    assert get_votes(1, 2, 'general') == pytest.approx(score, 0.01)


@pytest.mark.parametrize('votes', (
    # Seeing as the from and for nodes are directly connected, only the
    # votes from user 1 to user 2 are considered
    [1, 1, 1, 1],
    [1, 1, 2, 1],
    [1, 4, 1, 5],

    # The score gets scaled by the amount of votes given
    [12, 1, 1, 1],
    [13, 1, -1, 1],
    [14, 20, 1, 10000],
))
def test_get_votes_when_n_to_1(make_network, votes):
    # A lot of other users have voted for user 2
    #
    # user 1 ----\
    # user 3 ----->-- user 2
    # user 4 ----/
    # user 5 ---/
    #
    u1_u2, u3_u2, u4_u2, u5_u2 = votes
    graph = [
        (2, 1, u1_u2), (2, 3, u3_u2),
        (2, 4, u4_u2), (2, 5, u5_u2),
    ]

    make_network(graph)
    score = (1 - DECAY) * votes[0]
    assert get_votes(1, 2, 'general') == pytest.approx(score, 0.01)


@pytest.mark.parametrize('votes', (
    [1, 1, 1],
    [1, 1, 2],
    [1, 2, 1],
    [1, 2, 6],
    [100, 2, 6],
))
def test_get_votes_indirect(make_network, votes):
    # The following network is checked:
    #
    #         /- user2 -\
    #        /           \
    #  user1 --------------- user 3
    #
    u1_u2, u1_u3, u2_u3 = votes
    graph = [(2, 1, u1_u2), (3, 1, u1_u3), (3, 2, u2_u3)]

    make_network(graph)
    scale = (1 - DECAY)

    u3_2_score = scale * u2_u3 / (u2_u3 + u1_u3)
    u3_1_score = scale * u1_u3 / (u2_u3 + u1_u3)
    # The score from u3 is already decayed, but from u2 still needs to be
    u1_score =  u3_1_score + u3_2_score * scale

    assert get_votes(1, 3, 'general') == pytest.approx(u1_score * sum(votes), 0.01)


@pytest.mark.parametrize('votes', (
    [1, 1, 1, 1],
    [1, 1, 1, 2],
    [1, 2, 3, 4],
    [2, 1, 10, 1],
))
def test_get_votes_diamond(make_network, votes):
    # The following network is checked:
    #
    #            - user2 -
    #          /           \
    #  user1 <              >- user 4
    #          \           /
    #            - user3 -
    #
    u1_u2, u1_u3, u2_u4, u3_u4 = votes
    graph = [
        (2, 1, u1_u2), (3, 1, u1_u3),
        (4, 2, u2_u4), (4, 3, u3_u4),
    ]

    make_network(graph)
    scale = (1 - DECAY)

    u4_2_score = scale * u2_u4 / (u2_u4 + u3_u4)
    u4_3_score = scale * u3_u4 / (u2_u4 + u3_u4)
    u1_score = (u4_2_score + u4_3_score) * scale
    assert get_votes(1, 4, 'general') == pytest.approx(u1_score * sum(votes), 0.01)


@pytest.mark.parametrize('votes', (
    # Basic case where everyone cast a single vote
    {
        'user1': [1, 1, 1, 1],
        'user2': [1, 1],
        'user4': [1],
        'user5': [1],
        'user6': [1, 1]
    },
    # Direct connections have multiple votes
    {
        'user1': [3, 4, 8, 9],
        'user2': [1, 1],
        'user4': [1],
        'user5': [1],
        'user6': [1, 1]
    },
    # Indirect connections have multiple votes
    {
        'user1': [1, 1, 1, 1],
        'user2': [1, 23],
        'user4': [52],
        'user5': [1],
        'user6': [15, 12]
    },
    # Terminal nodes have multiple votes
    {
        'user1': [1, 1, 1, 1],
        'user2': [1, 1],
        'user4': [1],
        'user5': [1],
        'user6': [63, 51]
    },
    # Cycles are handled correctly
    {
        'user1': [1, 1, 1, 1],
        'user2': [1, 1],
        'user4': [1],
        'user5': [431],
        'user6': [1, 1]
    },
    # Every one has cast multiple votes
    {
        'user1': [23, 61, 923, 43],
        'user2': [84, 52],
        'user4': [99],
        'user5': [34],
        'user6': [58, 72]
    },
))
def test_get_votes_complicated_network(make_network, votes):
    # The following network is checked:
    #
    #        /--------------------------\
    #       /                           /
    #      /   /-- user2 -\--- user 5 -/
    #     /   /            \
    #  user1 <---- user3    >- user 6 -- user 7
    #         |\           /          \
    #         |  - user4 -             \
    #          \                        >- user 8
    #            ----------------------/
    u1_u2, u1_u3, u1_u4, u1_u8 = votes['user1']
    u2_u5, u2_u6 = votes['user2']
    u4_u6, = votes['user4']
    u5_u1, = votes['user5']
    u6_u7, u6_u8 = votes['user6']
    graph = [
        (2, 1, u1_u2), (3, 1, u1_u3), (4, 1, u1_u4), (8, 1, u1_u8),
        (5, 2, u2_u5), (6, 2, u2_u6),
        (6, 4, u4_u6),
        (1, 5, u5_u1),
        (7, 6, u6_u7), (8, 6, u6_u8),
    ]

    make_network(graph)
    scale = (1 - DECAY)

    # direct connections - users 2, 3 and 4
    assert get_votes(1, 2, 'general') == pytest.approx(scale * u1_u2, 0.01)
    assert get_votes(1, 3, 'general') == pytest.approx(scale * u1_u3, 0.01)
    assert get_votes(1, 4, 'general') == pytest.approx(scale * u1_u4, 0.01)

    # chain connections + cycle - user 5
    # User 5 has also voted for user 1 - this should be ignored when calculating the score
    score = scale * scale
    total_votes = u2_u5 + u1_u2
    assert get_votes(1, 5, 'general') == pytest.approx(score * total_votes, 0.01)

    # single layer indirect connections - user 6
    u6_2_score = scale * u2_u6 / (u2_u6 + u4_u6)
    u6_4_score = scale * u4_u6 / (u2_u6 + u4_u6)
    u6_score = (u6_2_score + u6_4_score) * scale
    u6_votes = u2_u6 + u1_u2 + u4_u6 + u1_u4
    assert get_votes(1, 6, 'general') == pytest.approx(u6_score * u6_votes, 0.01)

    # chain + diamond - user 7
    u7_score = u6_score * scale
    u7_votes = u6_votes + u6_u7
    assert get_votes(1, 7, 'general') == pytest.approx(u7_score * u7_votes, 0.01)

    # multiple combinations - user 8
    u8_6_score = scale * u6_u8 / (u6_u8 + u1_u8)
    u8_1_score = scale * u1_u8 / (u6_u8 + u1_u8)

    u8_score = u8_6_score * scale * scale + u8_1_score
    u8_votes = u6_votes + u6_u8 + u1_u8

    assert get_votes(1, 8, 'general') == pytest.approx(u8_score * u8_votes, 0.01)
