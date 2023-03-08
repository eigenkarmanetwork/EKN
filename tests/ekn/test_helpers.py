import pytest
from tempfile import TemporaryDirectory
from unittest.mock import MagicMock, patch

from ekn.database import DatabaseManager
from ekn.helpers import (
    get_params, get_where_str, get_users_index, get_network,
)


@pytest.fixture
def db():
    with TemporaryDirectory() as folder:
        db_file = folder + '/test.db'
        with DatabaseManager(db_file) as database:
            with patch('ekn.helpers.DatabaseManager', return_value=DatabaseManager(db_file)):
                yield database


def make_network(db, votes):
    for from_, to in votes:
        db.execute(
            "INSERT INTO votes (user_from, user_to, count, category) VALUES (?, ?, ?, ?)",
            (from_, to, 1, 'general'),
        )
        db.commit()


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


def test_get_network(db):
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
    make_network(db, votes)
    assert get_network(1, "WHERE 1=1") == set(range(1, 10))


def test_get_network_sparse(db):
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
    make_network(db, votes)
    assert get_network(1, "WHERE 1=1") == {1, 2, 5, 6}


def test_get_network_cycle(db):
    votes = [(1, 2), (2, 3), (3, 4), (4, 5), (5, 1)]
    make_network(db, votes)
    assert get_network(1, "WHERE 1=1") == {1, 2, 3, 4, 5}
