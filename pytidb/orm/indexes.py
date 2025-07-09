from typing import Literal, Union
from sqlalchemy import text
from sqlalchemy.sql.schema import Index
from pytidb.orm.sql.ddl import TiDBSchemaGenerator
from pytidb.orm.types import DistanceMetric, validate_distance_metric


"""
The algorithm used for vector index.

Available algorithms:
  HNSW: Hierarchical Navigable Small World graph.
"""
VectorIndexAlgorithm = Literal["HNSW"]


def format_distance_expression(
    column_name: str, distance_metric: DistanceMetric
) -> str:
    distance_fn = distance_metric.to_sql_func()
    return f"({distance_fn}({column_name}))"


class VectorIndex(Index):
    """Vector Index schema."""

    def __init__(
        self,
        name,
        *columns,
        distance_metric: Union[DistanceMetric, str] = DistanceMetric.COSINE,
        algorithm: VectorIndexAlgorithm = "HNSW",
        ensure_columnar_replica: bool = True,
        **kw,
    ):
        if len(columns) == 0:
            raise ValueError("Vector index must have at least one column")
        if len(columns) > 1:
            raise ValueError(
                f"Vector index can only apply to one column, but got {len(columns)} columns"
            )
        if algorithm not in ["HNSW"]:
            raise ValueError(f"Invalid vector index algorithm: {algorithm}")

        distance_metric = validate_distance_metric(distance_metric)

        # Convert column name to distance expression.
        vector_column = columns[0]
        table = kw.get("table", None)
        if isinstance(vector_column, str):
            vector_column_name = vector_column
            distance_expression = format_distance_expression(
                vector_column_name, distance_metric
            )
        elif hasattr(vector_column, "table"):
            table = vector_column.table
            vector_column_name = vector_column.name
            distance_expression = format_distance_expression(
                vector_column_name, distance_metric
            )
        else:
            raise ValueError(f"Invalid vector column: {vector_column}")
        expressions = [text(distance_expression)]

        self.distance_metric = distance_metric
        self.ensure_columnar_replica = ensure_columnar_replica
        kw["mysql_prefix"] = "VECTOR"
        kw["mysql_using"] = algorithm
        super().__init__(name, *expressions, _table=table, **kw)

    def create(self, bind, checkfirst: bool = False) -> None:
        bind._run_ddl_visitor(TiDBSchemaGenerator, self, checkfirst=checkfirst)


"""
Parser used for full text index.

Available parsers:
  STANDARD: Fast parser for English content, splits words by spaces and punctuation.
  MULTILINGUAL: Supports multiple languages including English, Chinese, Japanese, and Korean.
"""
FullTextParser = Literal["STANDARD", "MULTILINGUAL"]


class FullTextIndex(Index):
    """Full Text Index schema."""

    def __init__(
        self,
        name,
        *column_names,
        fts_parser: FullTextParser = "MULTILINGUAL",
        ensure_columnar_replica: bool = True,
        **kw,
    ):
        if fts_parser not in ["STANDARD", "MULTILINGUAL"]:
            raise ValueError(f"Invalid full text parser: {fts_parser}")
        self.ensure_columnar_replica = ensure_columnar_replica
        kw["mysql_prefix"] = "FULLTEXT"
        kw["mysql_with_parser"] = fts_parser
        super().__init__(name, *column_names, **kw)
