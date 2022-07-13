from etn.database import DatabaseManager
from etn.routes import (
    get_score,
    register_connection,
    register_service,
    register_user,
    verify_credentials,
    version,
    vote,
)
from flask import Flask


DatabaseManager()  # Update DB
app = Flask(__name__)


app.add_url_rule("/get_score", view_func=get_score, methods=["POST"])
app.add_url_rule("/register_connection", view_func=register_connection, methods=["POST"])
app.add_url_rule("/register_service", view_func=register_service, methods=["POST"])
app.add_url_rule("/register_user", view_func=register_user, methods=["POST"])
app.add_url_rule("/verify_credentials", view_func=verify_credentials, methods=["POST", "OPTIONS"])
app.add_url_rule("/version", view_func=version, methods=["GET"])
app.add_url_rule("/vote", view_func=vote, methods=["POST"])
