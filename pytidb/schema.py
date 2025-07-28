from typing import Any, Literal, Optional, TYPE_CHECKING, List, TypedDict

from pydantic import BaseModel
from sqlalchemy import Column, Index
from sqlmodel import SQLModel, Field, Relationship
from sqlmodel.main import FieldInfo, RelationshipInfo, SQLModelMetaclass

from pytidb.orm.types import TEXT, VECTOR
from pytidb.orm.indexes import VectorIndexAlgorithm
from pytidb.orm.distance_metric import DistanceMetric


if TYPE_CHECKING:
    from pytidb.embeddings.base import BaseEmbeddingFunction, EmbeddingSourceType


VectorDataType = List[float]

IndexType = Literal["vector", "fulltext", "scalar"]


class QueryBundle(TypedDict):
    query: Optional[Any]
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
    source_type: "EmbeddingSourceType" = "text",
    index: Optional[bool] = None,
    distance_metric: Optional[DistanceMetric] = DistanceMetric.COSINE,
    algorithm: Optional[VectorIndexAlgorithm] = "HNSW",
    **kwargs,
):
    # Notice: Currently, only L2 and COSINE distance metrics support indexing.
    if index is None:
        if distance_metric in [DistanceMetric.L2, DistanceMetric.COSINE]:
            index = True
        else:
            index = False

    sa_column = kwargs.pop("sa_column", Column(VECTOR(dimensions)))

    return Field(
        sa_column=sa_column,
        schema_extra={
            "field_type": "vector",
            "dimensions": dimensions,
            # Auto embedding related.
            "embed_fn": embed_fn,
            "source_field": source_field,
            "source_type": source_type,
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
    sa_column = kwargs.pop("sa_column", Column(TEXT))
    return Field(
        sa_column=sa_column,
        schema_extra={
            "field_type": "text",
            # Fulltext index related.
            "skip_index": not index,
            "fts_parser": fts_parser,
        },
        **kwargs,
    )


class ColumnInfo(BaseModel):
    column_name: str
    column_type: str
