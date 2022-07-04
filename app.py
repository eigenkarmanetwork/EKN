from etn.database import DatabaseManager
from flask import Flask, Response, request
import hashlib
import secrets

app = Flask(__name__)

@app.route("/register_user", methods=["POST"])
def register_user() -> Response:
    """
    Message Structure:
    {
        "username": str
        "password": str (SHA512 Hex Digest)
    }

    Returns:
    409: Username is not available.
    200: Success.
    """
    if request.is_json:
        message = request.get_json()
        assert isinstance(message, dict)
        username = message["username"]
        password = message["password"]
    else:
        username = request.form.get("username")
        password = request.form.get("password")

    salt = secrets.token_hex(6)
    sha512 = hashlib.new("sha512")
    sha512.update(f"{password}:{salt}".encode("utf8"))
    password_hash = sha512.hexdigest()
    with DatabaseManager() as db:
        print(username)
        result = db.execute("SELECT * FROM users WHERE username=:username", {"username": username})
        if result.fetchone():
            return Response("Username is not available.", 409)  # 409: Conflict
        db.execute("INSERT INTO users (username, password, salt) VALUES (?, ?, ?)", (username, password_hash, salt))
    return Response("Registration Successful", 200)
