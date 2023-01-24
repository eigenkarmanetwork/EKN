import getpass
import json
import requests

headers = {"Content-type": "application/json", "Accept": "text/plain"}
name = input("Service: ")
data = {"name": name}
r = requests.post(
    "http://127.0.0.1:31415/register_service", data=json.dumps(data), headers=headers
)
print(f"{r.status_code}: {r.text}")
