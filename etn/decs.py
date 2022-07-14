from werkzeug.datastructures import Headers
from flask import Response
from typing import Callable
import functools


def allow_cors(_func = None, *, host = "http://www.eigentrust.net") -> Callable[..., Response | Callable[..., Response]]:
    def cors_decorator(func: Callable[..., Response]) -> Callable[..., Response]:
        @functools.wraps(func)
        def cors_wrapper(*args, **kwargs) -> Response:
            response = func(*args, **kwargs)
            if response.headers.get("Access-Control-Allow-Origin") is None:
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
