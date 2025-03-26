import enum
from typing import Optional, TYPE_CHECKING, List

from pydantic import BaseModel
from sqlalchemy import Column
from sqlmodel import SQLModel, Field, Relationship
from sqlmodel.main import FieldInfo, RelationshipInfo
from tidb_vector.sqlalchemy import VectorType

if TYPE_CHECKING:
    from pytidb.embeddings.base import BaseEmbeddingFunction

VectorDataType = List[float]


class TableModel(SQLModel):
    pass


Field = Field
Relationship = Relationship
Column = Column
FieldInfo = FieldInfo
RelationshipInfo = RelationshipInfo


def VectorField(
    dimensions: int,
    source_field: Optional[str] = None,
    embed_fn: Optional["BaseEmbeddingFunction"] = None,
    **kwargs,
):
    return Field(
        sa_column=Column(VectorType(dimensions)),
        schema_extra={
            "embed_fn": embed_fn,
            "dimensions": dimensions,
            "source_field": source_field,
        },
        **kwargs,
    )


class DistanceMetric(enum.Enum):
    """
    An enumeration representing different types of distance metrics.

    - `DistanceMetric.L2`: L2 (Euclidean) distance metric.
    - `DistanceMetric.COSINE`: Cosine distance metric.
    """

    L2 = "L2"
    COSINE = "COSINE"

    def to_sql_func(self):
        """
        Converts the DistanceMetric to its corresponding SQL function name.

        Returns:
            str: The SQL function name.

        Raises:
            ValueError: If the DistanceMetric enum member is not supported.
        """
        if self == DistanceMetric.L2:
            return "VEC_L2_DISTANCE"
        elif self == DistanceMetric.COSINE:
            return "VEC_COSINE_DISTANCE"
        else:
            raise ValueError("unsupported distance metric")


class ColumnInfo(BaseModel):
    column_name: str
    column_type: str
