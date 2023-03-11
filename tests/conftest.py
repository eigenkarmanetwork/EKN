import pytest
from tempfile import TemporaryDirectory
from unittest.mock import MagicMock, patch

from ekn.database import DatabaseManager


@pytest.fixture
def db():
    with TemporaryDirectory() as folder:
        db_file = folder + '/test.db'
        with DatabaseManager(db_file) as database:
            with patch('ekn.helpers.DatabaseManager', return_value=DatabaseManager(db_file)):
                yield database


@pytest.fixture
def make_network(db):
    def creator(votes):
        for vote in votes:
            if len(vote) == 2:
                vote = list(vote) + [1]
            if len(vote) == 3:
                vote = list(vote) + ['general']

            db.execute(
                "INSERT INTO votes (user_from, user_to, count, category) VALUES (?, ?, ?, ?)",
                vote
            )
            db.commit()
    return creator


@pytest.fixture
def network(make_network):
    votes = [
        (2, 1),
        # Make sure there are other networks in the database
        (200, 201), (201, 200),
    ]
    make_network(votes)


# Add a command to run slow tests - this will by default skip tests marked as slow
def pytest_addoption(parser):
    parser.addoption(
        "--runslow", action="store_true", default=False, help="run slow tests"
    )


def pytest_configure(config):
    config.addinivalue_line("markers", "slow: mark test as slow to run")


def pytest_collection_modifyitems(config, items):
    if config.getoption("--runslow"):
        # --runslow given in cli: do not skip slow tests
        return
    skip_slow = pytest.mark.skip(reason="need --runslow option to run")
    for item in items:
        if "slow" in item.keywords:
            item.add_marker(skip_slow)
