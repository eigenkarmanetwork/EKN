import getpass
import json
import requests

headers = {"Content-type": "application/json", "Accept": "text/plain"}
username = input("Username: ")
password = getpass.getpass("Password: ")
data = {"username": username, "password": password}
r = requests.post(
    "http://127.0.0.1:31415/register_user", data=json.dumps(data), headers=headers
)
print(f"{r.status_code}: {r.text}")
