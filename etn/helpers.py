from flask import request
from typing import Any


def get_params(params: list[str]) -> Any:
    ret = []
    if request.is_json:
        message = request.get_json()
        assert isinstance(message, dict)
        for param in params:
            if param in params:
                ret.append(message[param])
            else:
                ret.append(None)
    else:
        for param in params:
            ret.append(request.form.get(param, None))
    if len(ret) == 1:
        return ret[0]
    elif len(ret) == 0:
        return None
    return ret
