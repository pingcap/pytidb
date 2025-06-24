import enum
from typing import Literal, Optional, TYPE_CHECKING, List, TypedDict

from pydantic import BaseModel
from sqlalchemy import Column, Index
from sqlmodel import SQLModel, Field, Relationship
from sqlmodel.main import FieldInfo, RelationshipInfo, SQLModelMetaclass
from tidb_vector.sqlalchemy import VectorType

from pytidb.orm.indexes import VectorIndexAlgorithm, DistanceMetric

if TYPE_CHECKING:
    from pytidb.embeddings.base import BaseEmbeddingFunction

VectorDataType = List[float]


IndexType = Literal["vector", "fulltext", "scalar"]


class QueryBundle(TypedDict):
    query_text: Optional[str]
    query_vector: Optional[VectorDataType]


class TableModelMeta(SQLModelMetaclass):
    def __new__(mcs, name, bases, namespace, **kwargs):
        if name != "TableModel":
            kwargs.setdefault("table", True)
        return super().__new__(mcs, name, bases, namespace, **kwargs)


class TableModel(SQLModel, metaclass=TableModelMeta):
    pass


Field = Field
Relationship = Relationship
Column = Column
Index = Index
FieldInfo = FieldInfo
RelationshipInfo = RelationshipInfo


def VectorField(
    dimensions: int,
    source_field: Optional[str] = None,
    embed_fn: Optional["BaseEmbeddingFunction"] = None,
    index: Optional[bool] = True,
    distance_metric: Optional[DistanceMetric] = "COSINE",
    algorithm: Optional[VectorIndexAlgorithm] = "HNSW",
    **kwargs,
):
    return Field(
        sa_column=Column(VectorType(dimensions)),
        schema_extra={
            "field_type": "vector",
            "dimensions": dimensions,
            # Auto embedding related.
            "embed_fn": embed_fn,
            "source_field": source_field,
            # Vector index related.
            "skip_index": not index,
            "distance_metric": distance_metric,
            "algorithm": algorithm,
        },
        **kwargs,
    )


def FullTextField(
    index: Optional[bool] = True,
    fts_parser: Optional[str] = "MULTILINGUAL",
    **kwargs,
):
    return Field(
        schema_extra={
            "field_type": "text",
            # Fulltext index related.
            "skip_index": not index,
            "fts_parser": fts_parser,
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
