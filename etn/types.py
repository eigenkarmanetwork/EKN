from typing import Callable, Optional, TYPE_CHECKING
from collections.abc import Iterable

if TYPE_CHECKING:
    from etn.database import DatabaseManager

SQL_PARAM = tuple[int | str | bool | float, ...]
SQL_PARAMS = Optional[SQL_PARAM | Iterable[SQL_PARAM]]

DATABASE_VERSIONS = dict[str, Callable[["DatabaseManager"], None] | None]
