from etn.database import DatabaseManager
from etn.routes import (
    register_user,
    register_service,
    register_connection,
    vote
)
from flask import Flask


DatabaseManager()  # Update DB
app = Flask(__name__)


app.add_url_rule("/register_user", view_func=register_user, methods=["POST"])
app.add_url_rule("/register_service", view_func=register_service, methods=["POST"])
app.add_url_rule("/register_connection", view_func=register_connection, methods=["POST"])
app.add_url_rule("/vote", view_func=vote, methods=["POST"])
