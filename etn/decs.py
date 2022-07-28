from werkzeug.datastructures import Headers
from flask import Response, request
from typing import Callable, Optional
import functools


def allow_cors(
    _func=None, *, hosts: Optional[list] = None, custom_options=False
) -> Callable[..., Response | Callable[..., Response]]:

    def cors_decorator(func: Callable[..., Response]) -> Callable[..., Response]:
        @functools.wraps(func)
        def cors_wrapper(*args, **kwargs) -> Response:
            try:
                if not hosts is None:
                    hosts = ["http://www.eigentrust.net", "http://eigentrust.net"]
            except Exception:
                hosts = ["http://www.eigentrust.net", "http://eigentrust.net"]
            if request.method == "OPTIONS" and not custom_options:
                response = Response()
            else:
                response = func(*args, **kwargs)
            if response.headers.get("Access-Control-Allow-Origin") is None:
                if "*" in hosts:
                    host = "*"
                elif request.headers.get("Origin") in hosts:
                    host = request.headers.get("Origin")
                else:
                    host = hosts[0]
                response.headers.add("Access-Control-Allow-Origin", host)
            if response.headers.get("Access-Control-Allow-Headers") is None:
                response.headers.add("Access-Control-Allow-Headers", "Content-type")
            if response.headers.get("Vary"):
                vary = response.headers.get("Vary")
                varying = vary.split(", ")
                if "Origin" not in varying:
                    vary += ", Origin"
                    response.headers.remove("Vary")
                    response.headers.add("Vary", vary)
            else:
                response.headers.add("Vary", "Origin")
            return response

        return cors_wrapper

    if _func is None:
        return cors_decorator
    else:
        return cors_decorator(_func)
