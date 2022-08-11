from etn.database import DatabaseManager
from etn.routes import (
    categories,
    change_security,
    gdpr_view,
    get_score,
    get_current_key,
    get_vote_count,
    register_connection,
    register_service,
    register_user,
    registration,
    verify_credentials_hash_route,
    verify_credentials_route,
    version,
    vote,
)
from flask import Flask


DatabaseManager()  # Update DB
app = Flask(__name__)


app.add_url_rule("/categories", view_func=categories, methods=["GET", "OPTIONS"])
app.add_url_rule("/change_security", view_func=change_security, methods=["POST", "OPTIONS"])
app.add_url_rule("/gdpr_view", view_func=gdpr_view, methods=["POST", "OPTIONS"])
app.add_url_rule("/get_score", view_func=get_score, methods=["POST", "OPTIONS"])
app.add_url_rule("/get_current_key", view_func=get_current_key, methods=["POST", "OPTIONS"])
app.add_url_rule("/get_vote_count", view_func=get_vote_count, methods=["POST", "OPTIONS"])
app.add_url_rule("/register_connection", view_func=register_connection, methods=["POST", "OPTIONS"])
app.add_url_rule("/register_service", view_func=register_service, methods=["POST", "OPTIONS"])
app.add_url_rule(
    "/register_temp_user", view_func=registration.register_temp_user, methods=["POST", "OPTIONS"]
)
app.add_url_rule("/register_user", view_func=register_user, methods=["POST", "OPTIONS"])
app.add_url_rule(
    "/verify_credentials_hash", view_func=verify_credentials_hash_route, methods=["POST", "OPTIONS"]
)
app.add_url_rule("/verify_credentials", view_func=verify_credentials_route, methods=["POST", "OPTIONS"])
app.add_url_rule("/version", view_func=version, methods=["GET"])
app.add_url_rule("/vote", view_func=vote, methods=["POST", "OPTIONS"])
