#!/usr/bin/env python3
import random
import requests
from itertools import combinations


USERS = 50
SERVICES = 10
PASSWORD = 'hunter2'
SERVER = 'http://127.0.0.1:31415'


def retry(times=3):
    def decorator(func):
        def wrapper(*args, **kwargs):
            for i in range(times):
                try:
                    return func(*args, **kwargs)
                except requests.ConnectionError as e:
                    if i == times - 1:
                        raise
        return wrapper
    return decorator


@retry(3)
def send(endpoint, data={}):
    return requests.post(SERVER + endpoint, json=data)


@retry(3)
def fetch(endpoint, data={}):
    return requests.get(SERVER + endpoint, json=data)


def generate_names(prefix):
    i = 1
    while True:
        yield f'{prefix}_{i}'
        i += 1


def take(n, coll):
    """Return the first n items of the given iterable."""
    return (i for _, i in zip(range(n), coll))


def connect_service_users(per_service, services):
    print('Connecting service users')
    for service, users in per_service.items():
        print(f'  - {service}')
        for user in users:
            send(
                '/register_connection', {
                    "service_name": service,
                    "service_key": services[service],
                    "service_user": f'{service}_{user}',
                    "username": user,
                    "password": PASSWORD,
                })


def vote_handler(endpoint, services, per_service):
    def handler(service, from_user, to_user):
        users = per_service[service]
        if from_user not in users or to_user not in users:
            return "Not in service"

        return send(endpoint, {
            "service_name": service,
            "service_key": services[service],
            "for": f'{service}_{to_user}',
            "from": f'{service}_{from_user}',
            "password": PASSWORD,
        })
    return handler


def generate_votes(vote, per_service):
    print('Generating votes:')
    for service, users in per_service.items():
        print(f'  - {service}')
        for user1, user2 in combinations(users, 2):
            for _ in range(random.randint(0, 20)):
                vote(service, user1, user2)


def generate_all():
    services = {
        name: send('/register_service', {'name': name}).text
        for name in take(SERVICES, generate_names('service'))
    }
    users = {
        name: send('/register_user', {'username': name, 'password': PASSWORD}).text
        for name in take(USERS, generate_names('user'))
    }
    per_service = {
        service: random.sample(sorted(users), random.randint(1, USERS))
        for service in services
    }

    vote = vote_handler('/vote', services, per_service)
    # votes = vote_handler('/get_vote_count', services, per_service)
    # score = vote_handler('/get_score', services, per_service)

    connect_service_users(per_service, services)
    generate_votes(vote, per_service)


if __name__ == "__main__":
    try:
        fetch('/version')
    except requests.ConnectionError as e:
        print('ERROR: Could not connect to server. Is it up?')
        exit(1)
    generate_all()
