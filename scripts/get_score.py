import getpass
import json
import requests

headers = {"Content-type": "application/json", "Accept": "text/plain"}
key = input("Service Key: ")
for_user = input("For: ")
from_user = input("From: ")
password = getpass.getpass("Password: ")
data = {"service": key, "for": for_user, "from": from_user, "password": password}
r = requests.post("http://127.0.0.1:31415/get_score", data=json.dumps(data), headers=headers)
print(f"{r.status_code}: {r.text}")
