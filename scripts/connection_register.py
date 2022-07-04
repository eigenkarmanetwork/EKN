import getpass
import json
import requests

headers = {"Content-type": "application/json", "Accept": "text/plain"}
service = input("Service Key: ")
service_user = input("Service User: ")
username = input("Username: ")
password = getpass.getpass("Password: ")
data = {"service": service, "service_user": service_user, "username": username, "password": password}
r = requests.post("http://127.0.0.1:31415/register_connection", data=json.dumps(data), headers=headers)
print(f"{r.status_code}: {r.text}")
