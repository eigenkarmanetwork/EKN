import json
import random
import itertools
import logging
import time
from pathlib import Path

import pytest
from ekn.helpers import get_votes


logger = logging.getLogger(__file__)
data_dir = Path(__file__).parent.parent / 'data'


def generate_network(make_network, title, n_users=150, prob_vote=0.2, max_votes=100):
    """Make a network with random votes.

    :param title: the name of the resulting file
    :param n_users: how many users will be created
    :param prob_vote: how likely a user will vote for a different user
    :param max_votes: given that a user will vote for someone, this is the max amount of votes they'll give them
    """
    def make_votes():
        if random.random() < prob_vote:
            return random.randint(1, max_votes)
        return 0

    users = list(range(1, n_users + 1))
    user_combinations = list(itertools.combinations(users, 2))
    raw_weights = list(filter(
        lambda x: x[2],
        ((from_, to, make_votes()) for from_, to in user_combinations)
    ))
    logger.info('got weights')

    make_network(raw_weights)
    logger.info('made network')
    scores = [
        (from_, to, get_votes(to, from_, 'general')) for from_, to in user_combinations
    ]
    logger.info('got scores')

    with open(data_dir / f'network-{title}.json', 'w') as f:
        json.dump({'weights': raw_weights, 'scores': [i for i in scores if i[2] > 0]}, f)


@pytest.mark.slow
@pytest.mark.parametrize('network_type', ('sparse', 'average', 'dense'))
def test_saved_networks(network_type, make_network):
    with open(data_dir / f'network-{network_type}.json') as f:
        data = json.load(f)

    make_network(data['weights'])
    scores = data['scores']

    start = time.time()
    for from_, to, score in scores:
        assert get_votes(to, from_, 'general') == pytest.approx(score, 0.01)
    total_time = time.time() - start
    print(f'Took {total_time:.2f}s to check {len(scores)} items with scores: {1000 * total_time / len(scores):.2f}ms per item')

    max_user = max({i[0] for i in data['weights']})
    with_scores = {(from_, to) for from_, to, _ in scores}
    without_scores = [
        item for item in itertools.combinations(list(range(1, max_user + 1)), 2)
        if item not in with_scores
    ]

    start = time.time()
    for from_, to in without_scores:
        if (from_, to) not in with_scores:
            assert get_votes(to, from_, 'general') == 0.0
    total_time = time.time() - start
    print(f'Took {total_time:.2f}s to check {len(without_scores)} items without scores: {1000 * total_time / len(without_scores):.2f}ms per item')
