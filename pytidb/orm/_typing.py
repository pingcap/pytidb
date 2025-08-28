from typing import TYPE_CHECKING, Union

if TYPE_CHECKING:
    from sqlalchemy.engine import Engine, Connection, MockConnection


_CreateDropBind = Union["Engine", "Connection", "MockConnection"]
