from typing import (
    TYPE_CHECKING,
    Any,
    Dict,
    List,
    Literal,
    Optional,
    Union,
    Tuple,
    Sequence,
    TypeVar,
    Generic,
)

from pydantic import BaseModel, Field
from sqlalchemy import Row, Select, asc, desc, literal, select, and_, text
from pytidb.functions import fts_match_word
from pytidb.rerankers.base import BaseReranker
from pytidb.schema import DistanceMetric, QueryBundle, VectorDataType, TableModel
from pytidb.utils import (
    build_filter_clauses,
    check_text_column,
    check_vector_column,
    get_row_id_from_row,
    merge_result_rows,
)
from pytidb.logger import logger


if TYPE_CHECKING:
    from pytidb.table import Table
    from pandas import DataFrame


SearchType = Literal["vector", "fulltext", "hybrid"]


DISTANCE_LABEL = "_distance"
MATCH_SCORE_LABEL = "_match_score"
SCORE_LABEL = "_score"
ROW_ID_LABEL = "_tidb_rowid"

T = TypeVar("T", bound=TableModel)


class SearchResult(BaseModel, Generic[T]):
    hit: T
    distance: Optional[float] = Field(
        description="The distance between the query vector and the vectors in the table.",
        default=None,
    )
    match_score: Optional[float] = Field(
        description="The match score between the query text and the text in the table.",
        default=None,
    )
    score: Optional[float] = Field(
        description="The score of the search result.",
        default=None,
    )

    def __getattr__(self, item: str):
        if hasattr(self.hit, item):
            return getattr(self.hit, item)
        raise AttributeError(
            f"'{self.__class__.__name__}' object has no attribute '{item}'"
        )

    @property
    def similarity_score(self) -> float:
        if self.distance is not None:
            return 1 - self.distance
        else:
            return None


class SearchQuery:
    def __init__(
        self,
        table: "Table",
        search_type: SearchType = "vector",
        query: Optional[Union[VectorDataType, str, QueryBundle]] = None,
    ):
        # Table.
        self._table = table
        self._sa_table = table._sa_table
        self._client = table.client
        self._columns = table._columns
        self._vector_column = table.vector_column
        self._text_column = table.text_column

        # Query.
        self._search_type = search_type
        self._query = query
        if isinstance(query, dict):
            self._query_vector = query["query_vector"]
            self._query_text = query["query_text"]
        else:
            self._query_vector = query if isinstance(query, list) else None
            self._query_text = query if isinstance(query, str) else None

        # Vector search.
        self._distance_metric = DistanceMetric.COSINE
        self._distance_threshold = None
        self._distance_lower_bound = None
        self._distance_upper_bound = None
        self._filters = None
        self._num_candidate = 20

        # Reranker.
        self._reranker = None
        self._rerank_field_name = None

        # Miscellaneous.
        self._debug = False
        self._limit = None

    def vector(self, query_vector: VectorDataType):
        self._query_vector = query_vector
        return self

    def text(self, query_text: str):
        self._query_text = query_text
        return self

    def vector_column(self, column_name: str):
        self._vector_column = check_vector_column(self._columns, column_name)
        return self

    def text_column(self, column_name: str):
        self._text_column = check_text_column(self._columns, column_name)
        return self

    def distance_metric(self, metric: DistanceMetric) -> "SearchQuery":
        self._distance_metric = metric
        return self

    def distance_threshold(self, threshold: Optional[float] = None) -> "SearchQuery":
        self._distance_threshold = threshold
        return self

    def distance_range(
        self, lower_bound: float = 0, upper_bound: float = 1
    ) -> "SearchQuery":
        self._distance_lower_bound = lower_bound
        self._distance_upper_bound = upper_bound
        return self

    def num_candidate(self, num_candidate: int) -> "SearchQuery":
        self._num_candidate = num_candidate
        return self

    def filter(self, filters: Optional[Dict[str, Any]] = None) -> "SearchQuery":
        self._filters = filters
        return self

    def limit(self, k: int) -> "SearchQuery":
        self._limit = k
        return self

    def debug(self, flag: bool = True) -> "SearchQuery":
        self._debug = flag
        return self

    def rerank(
        self, reranker: BaseReranker, rerank_field: Optional[str] = None
    ) -> "SearchQuery":
        """
        Rerank the search results.

        Reranker can be used for multiple-way (multi-vectors, hybrid) search result fusion or
        improve the quality of vector search results.

        Args:
            reranker: The reranker to use.
            rerank_field: The field to rerank on.
        """
        self._reranker = reranker
        self._rerank_field_name = rerank_field
        return self

    def _build_vector_query(self) -> Select:
        num_candidate = self._num_candidate if self._num_candidate else self._limit * 10

        if self._vector_column is None:
            if len(self._table.vector_columns) == 0:
                raise ValueError(
                    "vector column is not found, but is required for vector search"
                )
            elif len(self._table.vector_columns) >= 1:
                raise ValueError(
                    "more than two vector columns, please choice one through .vector_column()"
                )
            else:
                vector_column = self._table.vector_columns[0]
        else:
            vector_column = self._vector_column

        # Auto embedding
        if self._query_vector is None:
            if vector_column.name not in self._table.vector_field_configs:
                raise ValueError(
                    "query should be a vector, because the vector column didn't configure the embed_fn parameter"
                )

            config = self._table.vector_field_configs[vector_column.name]
            self._query_vector = config["embed_fn"].get_query_embedding(
                self._query_text
            )

        # Distance metric.
        if self._distance_metric == DistanceMetric.L2:
            distance_column = vector_column.l2_distance(self._query_vector).label(
                DISTANCE_LABEL
            )
        else:
            distance_column = vector_column.cosine_distance(self._query_vector).label(
                DISTANCE_LABEL
            )

        # Inner query for ANN search
        table_model = self._table.table_model
        columns = table_model.__table__.c
        inner_select_columns = list(columns)
        if self._sa_table.primary_key is None:
            inner_select_columns.insert(0, text("_tidb_rowid"))

        subquery_stmt = (
            select(
                *columns,
                distance_column,
            )
            .order_by(asc(DISTANCE_LABEL))
            .limit(num_candidate)
        )

        # Distance range.
        having = []
        if self._distance_lower_bound and self._distance_upper_bound:
            having.append(distance_column >= self._distance_lower_bound)
            having.append(distance_column <= self._distance_upper_bound)

        # Distance threshold.
        if self._distance_threshold:
            having.append(distance_column <= self._distance_threshold)

        if len(having) > 0:
            subquery_stmt = subquery_stmt.having(and_(*having))

        subquery = subquery_stmt.subquery("candidates")

        # Main query with metadata filters
        outer_select_columns = list(subquery.c)
        if self._sa_table.primary_key is None:
            outer_select_columns.insert(0, text("_tidb_rowid"))

        stmt = select(
            *outer_select_columns,
            (1 - subquery.c[DISTANCE_LABEL]).label(SCORE_LABEL),
        )

        if self._filters is not None:
            filter_clauses = build_filter_clauses(
                self._filters, subquery.c, table_model
            )
            stmt = stmt.filter(*filter_clauses)

        stmt = stmt.order_by(asc(DISTANCE_LABEL)).limit(self._limit)

        # Debug.
        if self._debug:
            db_engine = self._table.db_engine
            table_name = self._table.table_name
            compiled_sql = stmt.compile(
                dialect=db_engine.dialect, compile_kwargs={"literal_binds": True}
            )
            logger.info(
                f"Build vector search query on table <{table_name}>:\n{compiled_sql}"
            )

        return stmt

    def _build_fulltext_query(self) -> Select:
        if self._query_text is None:
            raise ValueError(
                "query string is required for fulltext search, please specify it through "
                ".text('<your query string>')"
            )

        if self._text_column is None:
            if len(self._table.text_columns) == 0:
                raise ValueError(
                    "no text column found in the table, fulltext search cannot be executed"
                )
            elif len(self._table.text_columns) >= 1:
                raise ValueError(
                    "more than two text columns in the table, need to specify one through"
                    ".text_column('<your text column name>')"
                )
            else:
                text_column = self._table.text_columns[0]
        else:
            text_column = self._text_column

        table_model = self._table.table_model
        columns = table_model.__table__.c
        select_columns = list(columns)
        if self._sa_table.primary_key is None:
            select_columns.insert(0, text("_tidb_rowid"))

        # TODO: support return score after fts_match_word is supported.
        table_name = self._table.table_name
        stmt = select(
            *select_columns,
            literal(None).label(MATCH_SCORE_LABEL),
            literal(None).label(SCORE_LABEL),
        ).filter(fts_match_word(self._query_text, text_column))

        if self._filters is not None:
            filter_clauses = build_filter_clauses(self._filters, columns, table_model)
            stmt = stmt.filter(*filter_clauses)

        stmt = stmt.order_by(desc(fts_match_word(self._query_text, text_column))).limit(
            self._limit
        )

        # Debug.
        if self._debug:
            db_engine = self._table.db_engine
            table_name = self._table.table_name
            compiled_sql = stmt.compile(
                dialect=db_engine.dialect, compile_kwargs={"literal_binds": True}
            )
            logger.info(
                f"Build fulltext search query on table <{table_name}>:\n{compiled_sql}"
            )

        return stmt

    def _execute_query(self) -> Tuple[List[str], List[Any]]:
        if self._limit is None:
            raise ValueError(
                "limit is required for search, please specify it through " ".limit(n)"
            )

        if self._search_type == "vector":
            return self._exec_vector_query()
        elif self._search_type == "fulltext":
            return self._exec_fulltext_query()
        elif self._search_type == "hybrid":
            return self._exec_hybrid_query()
        else:
            raise ValueError(
                f"invalid search type: {self._search_type}, allowed search types are "
                "`vector`, `fulltext`, and `hybrid`"
            )

    def _exec_vector_query(self) -> Tuple[List[str], List[Row]]:
        with self._client.session() as db_session:
            vector_query = self._build_vector_query()
            result = db_session.execute(vector_query)
            keys = result.keys()
            rows = result.fetchall()

            # Apply reranker to improve the accuracy of vector search results. (Optional)
            if self._reranker is not None:
                rows = self._rerank_result_set(rows)

            return keys, rows

    def _exec_fulltext_query(self) -> Tuple[List[str], List[Row]]:
        with self._client._db_engine.connect() as conn:
            query = self._build_fulltext_query()
            result = conn.execute(query)
            keys = result.keys()
            rows = result.fetchall()

        # Apply reranker to improve the accuracy of fulltext search results. (Optional)
        if self._reranker is not None:
            rows = self._rerank_result_set(rows)

        return keys, rows

    def _exec_hybrid_query(self) -> Tuple[List[str], List[Row]]:
        with self._client.session() as db_session:
            vs_query = self._build_vector_query()
            vs_result = db_session.execute(vs_query)
            vs_rows = vs_result.fetchall()

            fts_query = self._build_fulltext_query()
            fts_result = db_session.execute(fts_query)
            fts_rows = fts_result.fetchall()

            # Merge the rows from vector search and fulltext search.
            def get_row_id(row: Row) -> Optional[int]:
                return get_row_id_from_row(row, self._sa_table)

            keys, rows = merge_result_rows(vs_rows, fts_rows, get_row_id)

            # Apply reranker to rerank the merged result set. (Optional)
            if self._reranker is not None:
                rows = self._rerank_result_set(rows)
            else:
                # Sort the rows by score.
                rows = sorted(
                    rows, key=lambda row: row._mapping[SCORE_LABEL] or 0, reverse=True
                )

            return keys, rows[: self._limit]

    def _rerank_result_set(self, rows: List[Row]) -> List[Row]:
        """
        Rerank the search results.

        Args:
            rows: The rows to rerank.

        Returns:
            The reranked rows.
        """
        rerank_field_name = self._get_rerank_field_name()

        if self._query_text is None:
            raise ValueError(
                "query text is required for reranker, please specify it through "
                ".text('<your query string>')"
            )

        documents = [row._mapping[rerank_field_name] for row in rows]
        reranked_results = self._reranker.rerank(
            self._query_text, documents, self._limit
        )
        reranked_rows = []
        for item in reranked_results:
            row = rows[item.index]
            score_index = row._key_to_index["_score"]
            _data = list(row._tuple())
            # Replace the score with the reranked score.
            _data[score_index] = item.relevance_score
            reranked_rows.append(
                Row(
                    row._parent,
                    None,
                    row._key_to_index,
                    tuple(_data),
                )
            )
        return reranked_rows

    def _get_rerank_field_name(self) -> str:
        if self._rerank_field_name is not None:
            return self._rerank_field_name

        if self._search_type in ["vector", "hybrid"]:
            if self._vector_column is not None:
                vector_field = self._table.vector_field_configs[
                    self._vector_column.name
                ]
                return vector_field["source_field_name"]

        if self._search_type == "fulltext":
            if self._text_column is not None:
                return self._text_column

        raise ValueError(
            "Please specify the rerank field name through .rerank(reranker, rerank_field_name)"
        )

    def to_rows(self) -> Sequence[Any]:
        _, rows = self._execute_query()
        return rows

    def to_list(self) -> List[dict]:
        keys, rows = self._execute_query()
        results = [dict(zip(keys, row)) for row in rows]
        return results

    def to_pydantic(self, with_score: Optional[bool] = True) -> List[BaseModel]:
        table_model = self._table.table_model

        _, rows = self._execute_query()
        results = []
        for row in rows:
            values: Dict[str, Any] = dict(row._mapping)
            distance = values.pop(DISTANCE_LABEL) if DISTANCE_LABEL in values else None
            match_score = (
                values.pop(MATCH_SCORE_LABEL) if MATCH_SCORE_LABEL in values else None
            )
            score = values.pop(SCORE_LABEL) if SCORE_LABEL in values else None
            hit = table_model.model_validate(values)

            if not with_score:
                results.append(hit)
            else:
                results.append(
                    SearchResult(
                        distance=distance,
                        match_score=match_score,
                        score=score,
                        hit=hit,
                    )
                )

        return results

    def to_pandas(self) -> "DataFrame":
        try:
            import pandas as pd
        except Exception:
            raise ImportError(
                "Failed to import pandas, please install it with `pip install pandas`"
            )

        keys, rows = self._execute_query()
        return pd.DataFrame(rows, columns=keys)
