from typing import Any, Literal, Optional, TYPE_CHECKING, List, TypedDict, Union
import json

from pydantic import BaseModel
from sqlalchemy import Column, Computed, Index
from sqlmodel import SQLModel, Field, Relationship
from sqlmodel.main import FieldInfo, RelationshipInfo, SQLModelMetaclass

from pytidb.sql import func
from pytidb.orm.types import TEXT, VECTOR
from pytidb.orm.indexes import VectorIndex, FullTextIndex, VectorIndexAlgorithm
from pytidb.orm.tiflash_replica import TiFlashReplica
from pytidb.orm.distance_metric import DistanceMetric, validate_distance_metric


if TYPE_CHECKING:
    from pytidb.embeddings.base import BaseEmbeddingFunction, EmbeddingSourceType


# Common objects.
DistanceMetric = DistanceMetric
validate_distance_metric = validate_distance_metric
VectorDataType = List[float]
IndexType = Literal["vector", "fulltext", "scalar"]


class QueryBundle(TypedDict):
    query: Optional[Any]
    query_vector: Optional[VectorDataType]


class ColumnInfo(BaseModel):
    column_name: str
    column_type: str


# SQLAlchemy objects.
Column = Column
Index = Index
VectorIndex = VectorIndex
FullTextIndex = FullTextIndex
TiFlashReplica = TiFlashReplica


# SQL Model objects.


class TableModelMeta(SQLModelMetaclass):
    def __new__(mcs, name, bases, namespace, **kwargs):
        if name != "TableModel":
            kwargs.setdefault("table", True)
        return super().__new__(mcs, name, bases, namespace, **kwargs)


class TableModel(SQLModel, metaclass=TableModelMeta):
    pass


Field = Field
Relationship = Relationship
FieldInfo = FieldInfo
RelationshipInfo = RelationshipInfo


def VectorField(
    dimensions: int,
    source_field: Optional[str] = None,
    embed_fn: Optional["BaseEmbeddingFunction"] = None,
    source_type: "EmbeddingSourceType" = "text",
    index: Optional[bool] = None,
    distance_metric: Optional[Union[DistanceMetric, str]] = DistanceMetric.COSINE,
    algorithm: Optional[VectorIndexAlgorithm] = "HNSW",
    **kwargs,
):
    # Notice: Currently, only L2 and COSINE distance metrics support indexing.
    distance_metric = validate_distance_metric(distance_metric)
    if index is None:
        if distance_metric in [DistanceMetric.L2, DistanceMetric.COSINE]:
            index = True
        else:
            index = False

    use_server = embed_fn.use_server if embed_fn else False
    if use_server:
        model_name = embed_fn.model_name
        embed_params = {
            **(embed_fn.server_embed_params or {}),
            **kwargs.get("server_embed_params", {}),
        }

        source_column = Column(source_field)
        if embed_params:
            embed_params_str = json.dumps(embed_params)
            embed_sql_function = func.EMBED_TEXT(
                model_name, source_column, embed_params_str
            )
        else:
            embed_sql_function = func.EMBED_TEXT(model_name, source_column)

        default_sa_column = Column(
            VECTOR(dimensions),
            Computed(embed_sql_function, persisted=True),
        )
    else:
        default_sa_column = Column(VECTOR(dimensions))

    sa_column = kwargs.pop("sa_column", default_sa_column)

    return Field(
        sa_column=sa_column,
        schema_extra={
            "field_type": "vector",
            "dimensions": dimensions,
            # Auto embedding related.
            "embed_fn": embed_fn,
            "source_field": source_field,
            "source_type": source_type,
            "use_server": use_server,
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
