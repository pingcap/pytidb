from abc import ABC, abstractmethod
from typing import Optional, List, Type

from sqlalchemy import Result
from pydantic import BaseModel, Field


class SQLExecuteResult(BaseModel):
    rowcount: int = Field(0)
    success: bool = Field(False)
    message: Optional[str] = Field(None)


class QueryResult(ABC):
    @abstractmethod
    def to_list(self) -> List[dict]:
        pass

    @abstractmethod
    def to_pydantic(self) -> List[BaseModel]:
        pass

    @abstractmethod
    def to_pandas(self):
        pass


class SQLModelQueryResult(QueryResult):
    def __init__(self, data: List[BaseModel]):
        self._data = data

    def to_list(self) -> List[dict]:
        return [item.model_dump() for item in self._data]

    def to_pydantic(self) -> List[BaseModel]:
        return self._data

    def to_pandas(self):
        try:
            import pandas as pd
        except Exception:
            raise ImportError(
                "Failed to import pandas, please install it with `pip install pandas`"
            )
        data = [item.model_dump() for item in self._data]
        return pd.DataFrame(data)


class SQLQueryResult(QueryResult):
    _result: Result

    def __init__(self, result):
        self._result = result

    def scalar(self):
        return self._result.scalar()

    def one(self):
        return self._result.one()

    def to_rows(self):
        return self._result.fetchall()

    def to_pandas(self):
        try:
            import pandas as pd
        except Exception:
            raise ImportError(
                "Failed to import pandas, please install it with `pip install pandas`"
            )
        keys = self._result.keys()
        rows = self._result.fetchall()
        return pd.DataFrame(rows, columns=keys)

    def to_list(self) -> List[dict]:
        keys = self._result.keys()
        rows = self._result.fetchall()
        return [dict(zip(keys, row)) for row in rows]

    def to_pydantic(self, model: Type[BaseModel]) -> List[BaseModel]:
        items = self.to_list()
        return [model.model_validate(item) for item in items]
