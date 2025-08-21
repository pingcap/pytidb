from pathlib import Path
from typing import (
    TYPE_CHECKING,
    Any,
    Callable,
    Dict,
    List,
    Literal,
    Optional,
    Union,
    Tuple,
    Sequence,
    TypeVar,
    Generic,
    overload,
)
from pydantic import BaseModel, Field
from sqlalchemy import Column, Row, Select, asc, desc, and_, text
from sqlmodel import select
from pytidb.orm.functions import fts_match_word
from pytidb.rerankers.base import BaseReranker
from pytidb.schema import QueryBundle, VectorDataType, TableModel
from pytidb.orm.distance_metric import DistanceMetric, validate_distance_metric
from pytidb.filters import build_filter_clauses
from pytidb.utils import (
    RowKeyType,
    check_text_column,
    check_vector_column,
    get_row_id_from_row,
)
from sqlalchemy.orm import aliased
from sqlalchemy.orm.util import AliasedClass
from pytidb.fusion import fusion_result_rows_by_rrf, fusion_result_rows_by_weighted
from pytidb.logger import logger


if TYPE_CHECKING:
    from pytidb.table import Table
    from pandas import DataFrame
    from PIL.Image import Image


SearchType = Literal["vector", "fulltext", "hybrid"]
FusionMethod = Literal["rrf", "weighted"]

INNER_HIT_LABEL = "_inner_hit"
HIT_LABEL = "_hit"
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


distance_function_map = {
    DistanceMetric.L2: "l2_distance",
    DistanceMetric.COSINE: "cosine_distance",
    DistanceMetric.L1: "l1_distance",
    DistanceMetric.NEGATIVE_INNER_PRODUCT: "negative_inner_product",
}
embed_distance_function_map = {
    DistanceMetric.L2: "embed_l2_distance",
    DistanceMetric.COSINE: "embed_cosine_distance",
    DistanceMetric.L1: "embed_l1_distance",
    DistanceMetric.NEGATIVE_INNER_PRODUCT: "embed_negative_inner_product",
}


class SearchQuery:
    def __init__(
        self,
        table: "Table",
        search_type: SearchType = "vector",
        query: Optional[Union[VectorDataType, str, Path, QueryBundle, "Image"]] = None,
    ):
        # Table information.
        self._table = table
        self._sa_table = table._sa_table
        self._client = table.client
        self._columns = table._columns

        # Search parameters.
        self._search_type = search_type
        self._vector_column = table._default_vector_column
        self._text_column = table._default_text_column
        self._limit = None
        self._debug = False

        # Query.
        self._query = None
        self._query_vector = None

        if isinstance(query, dict):
            self._query = query.get("query")
            self._query_vector = query.get("query_vector")
        elif isinstance(query, list):
            self._query_vector = query
        else:
            self._query = query

        # Vector search parameters.
        self._distance_metric = DistanceMetric.COSINE
        self._distance_threshold = None
        self._distance_lower_bound = None
        self._distance_upper_bound = None
        self._filters = None
        self._prefilter = False
        self._num_candidate = None

        # Reranker parameters.
        self._reranker = None
        self._rerank_field_name = None

        # Fusion parameters.
        self._fusion_method = "rrf"
        self._fusion_params = {
            "k": 60,
        }

    def vector(self, query_vector: VectorDataType):
        self._query_vector = query_vector
        return self

    def text(self, query_text: str):
        self._query = query_text
        return self

    def vector_column(self, column_name: str):
        self._vector_column = check_vector_column(self._columns, column_name)
        return self

    def text_column(self, column_name: str):
        self._text_column = check_text_column(self._columns, column_name)
        return self

    def distance_metric(self, metric: Union[DistanceMetric, str]) -> "SearchQuery":
        self._distance_metric = validate_distance_metric(metric)
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

    def filter(
        self, filters: Optional[Dict[str, Any]] = None, prefilter: bool = False
    ) -> "SearchQuery":
        self._filters = filters
        # Default mode is post-filter.
        self._prefilter = prefilter
        return self

    def limit(self, k: int) -> "SearchQuery":
        self._limit = k
        return self

    def debug(self, flag: bool = True) -> "SearchQuery":
        self._debug = flag
        return self

    @overload
    def fusion(self, method: Literal["rrf"], k: int = 60) -> "SearchQuery": ...

    @overload
    def fusion(
        self,
        method: Literal["weighted"],
        vs_weight: float = 0.5,
        fts_weight: float = 0.5,
    ) -> "SearchQuery": ...

    def fusion(self, method: FusionMethod = "rrf", **params) -> "SearchQuery":
        """
        Configure the fusion method for the search results.

        Args:
            method: The fusion method to use, supported methods are `rrf` and `weighted`.
            **params: The parameters for the fusion method.
        """
        if self._search_type != "hybrid":
            raise ValueError(
                "fusion method is only supported for hybrid search, please specify the "
                "search type through table.search(type='hybrid')"
            )

        if method not in ["rrf", "weighted"]:
            raise ValueError(
                "Invalid fusion method, supported methods: 'rrf', 'weighted'"
            )

        self._fusion_method = method
        self._fusion_params = params
        return self

    def rerank(
        self, reranker: BaseReranker, rerank_field: Optional[str] = None
    ) -> "SearchQuery":
        """
        Configure the rerank method for the search results.

        Reranker is a component that sorts search results using a specific model to
        improve search quality and relevance.

        Args:
            reranker: The reranker to use.
            rerank_field: The field to rerank on.
        """
        self._reranker = reranker
        self._rerank_field_name = rerank_field
        return self

    def _validate_vector_column(self) -> Column:
        if self._vector_column is None:
            if len(self._table.vector_columns) == 0:
                raise ValueError(
                    "no vector column found in table, but vector column is required for vector search"
                )
            elif len(self._table.vector_columns) >= 1:
                raise ValueError(
                    "more than two vector columns, please choice one through .vector_column()"
                )
            else:
                return self._table.vector_columns[0]
        else:
            return self._vector_column

    def _build_distance_column(self, vector_column: Column) -> Column:
        # Auto embedding for query.
        if self._query_vector is not None:
            # Already have query vector, no need for auto embedding
            use_server = False
        else:
            # Need to generate query vector through auto embedding
            auto_embedding_configs = self._table.auto_embedding_configs
            if vector_column.name not in auto_embedding_configs:
                raise ValueError(
                    "query should be a vector, because the vector column didn't "
                    "configure the embed_fn parameter"
                )

            config = auto_embedding_configs[vector_column.name]
            use_server = config.get("use_server", False)
            if not use_server:
                self._query_vector = config["embed_fn"].get_query_embedding(
                    self._query, config["source_type"]
                )

        # Distance metric mapping.
        if use_server:
            vector_op_name = embed_distance_function_map.get(self._distance_metric)
        else:
            vector_op_name = distance_function_map.get(self._distance_metric)

        if vector_op_name is None:
            raise ValueError(f"Invalid distance metric: {self._distance_metric}")

        # Pass the appropriate query value based on embedding mode.
        query_value = self._query if use_server else self._query_vector
        distance_column = getattr(vector_column, vector_op_name)(query_value).label(
            DISTANCE_LABEL
        )
        return distance_column

    def _apply_distance_condition(
        self, stmt: Select, distance_column: Column
    ) -> Select:
        having = []

        # Null vector values.
        #
        # Notice: This is a workaround to avoid records without vector value
        #         disappear in the front of the result set, which is caused by
        #         MySQL's default behavior of sorting NULL values to the head.
        #
        # TODO: Remove this workaround after TiDB return MAX_DISTANCE for NULL vector values.
        having.append(distance_column.isnot(None))

        # Distance range.
        if (
            self._distance_lower_bound is not None
            and self._distance_upper_bound is not None
        ):
            having.append(distance_column >= self._distance_lower_bound)
            having.append(distance_column <= self._distance_upper_bound)

        # Distance threshold.
        if self._distance_threshold:
            having.append(distance_column <= self._distance_threshold)

        if len(having) > 0:
            return stmt.having(and_(*having))
        else:
            return stmt

    def _get_aliased_column(
        self, aliased_class: AliasedClass, column: Column
    ) -> Column:
        columns = aliased_class._aliased_insp.local_table.c
        return columns[column.name]

    def _build_vector_query(self) -> Select:
        # Validate parameters.
        if self._query is None and self._query_vector is None:
            raise ValueError(
                "query is required for vector search, please specify it through "
                ".search('<query>', search_type='vector')"
            )

        vector_column = self._validate_vector_column()

        if self._prefilter:
            stmt = self._build_vector_query_with_pre_filter(vector_column)
        else:
            stmt = self._build_vector_query_with_post_filter(vector_column)

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

    def _build_vector_query_with_pre_filter(
        self, table_vector_column: Column
    ) -> Select:
        table_model = self._table.table_model

        hit = aliased(table_model, name=HIT_LABEL)
        vector_column = self._get_aliased_column(hit, table_vector_column)
        distance_column = self._build_distance_column(vector_column)

        stmt = select(
            hit,
            distance_column,
            (1 - distance_column).label(SCORE_LABEL),
        )

        if self._filters is not None:
            filter_clauses = build_filter_clauses(self._filters, hit)
            stmt = stmt.filter(*filter_clauses)

        stmt = self._apply_distance_condition(stmt, distance_column)
        stmt = stmt.order_by(asc(DISTANCE_LABEL)).limit(self._limit)

        return stmt

    def _build_vector_query_with_post_filter(
        self, table_vector_column: Column
    ) -> Select:
        table_model = self._table.table_model

        # Inner query for ANN search
        inner_hit = aliased(table_model, name=INNER_HIT_LABEL)
        inner_vector_column = self._get_aliased_column(inner_hit, table_vector_column)
        inner_distance_column = self._build_distance_column(inner_vector_column)
        inner_limit = self._num_candidate if self._num_candidate else self._limit * 10

        inner_stmt = select(inner_hit, inner_distance_column)
        inner_stmt = self._apply_distance_condition(inner_stmt, inner_distance_column)
        inner_stmt = inner_stmt.order_by(asc(DISTANCE_LABEL)).limit(inner_limit)
        inner_query = inner_stmt.subquery("candidates")

        # Outer query for post-filter.
        hit = aliased(table_model, inner_query, name=HIT_LABEL)
        vector_column = self._get_aliased_column(hit, table_vector_column)
        distance_column = self._build_distance_column(vector_column)

        stmt = select(
            hit,
            distance_column,
            (1 - distance_column).label(SCORE_LABEL),
        )

        if self._filters is not None:
            # In post-filter mode, apply filters to the subquery results
            filter_clauses = build_filter_clauses(self._filters, hit)
            stmt = stmt.filter(*filter_clauses)

        stmt = stmt.order_by(asc(DISTANCE_LABEL)).limit(self._limit)

        return stmt

    def _build_fulltext_query(self) -> Select:
        if self._query is None:
            raise ValueError(
                "query string is required for fulltext search, please specify it through "
                ".text('<your query string>')"
            )

        # Determine the text column.
        if self._text_column is None:
            if len(self._table.text_columns) == 0:
                raise ValueError(
                    "no text column found in the table, fulltext search cannot be executed"
                )
            elif len(self._table.text_columns) >= 1:
                raise ValueError(
                    "more than two text columns in the table, need to specify one through "
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

        table_name = self._table.table_name
        stmt = select(
            *select_columns,
            fts_match_word(self._query, text_column).label(MATCH_SCORE_LABEL),
            fts_match_word(self._query, text_column).label(SCORE_LABEL),
        ).filter(fts_match_word(self._query, text_column))

        if self._filters is not None:
            filter_clauses = build_filter_clauses(self._filters, self._table._sa_table)
            stmt = stmt.filter(*filter_clauses)

        stmt = stmt.order_by(desc(MATCH_SCORE_LABEL)).limit(self._limit)

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
                "limit is required for search, please specify it through .limit(n)"
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

            # Apply fusion method to merge the multiple result sets.
            keys, rows = self._fusion_result_set(vs_rows, fts_rows, get_row_id)

            # Apply reranker to rerank the merged result set. (Optional)
            if self._reranker is not None:
                rows = self._rerank_result_set(rows)
            else:
                # Sort the rows by score.
                rows = sorted(
                    rows, key=lambda row: row._mapping[SCORE_LABEL] or 0, reverse=True
                )

            return keys, rows[: self._limit]

    def _fusion_result_set(
        self,
        vs_rows: List[Row],
        fts_rows: List[Row],
        get_row_id: Callable[[Row], RowKeyType],
    ) -> Tuple[List[str], List[Row]]:
        """
        Fusion the search results.
        """
        if self._fusion_method == "rrf":
            k = self._fusion_params.get("k", self._limit)
            return fusion_result_rows_by_rrf(vs_rows, fts_rows, get_row_id, k=k)
        elif self._fusion_method == "weighted":
            vs_metric = self._distance_metric
            vs_weight = self._fusion_params.get("vs_weight", 0.5)
            fts_weight = self._fusion_params.get("fts_weight", 0.5)
            return fusion_result_rows_by_weighted(
                vs_rows=vs_rows,
                fts_rows=fts_rows,
                get_row_key=get_row_id,
                vs_metric=vs_metric,
                vs_weight=vs_weight,
                fts_weight=fts_weight,
            )
        else:
            raise ValueError(f"invalid fusion method: {self._fusion_method}")

    def _rerank_result_set(self, rows: List[Row]) -> List[Row]:
        """
        Rerank the search results.

        Args:
            rows: The rows to rerank.

        Returns:
            The reranked rows.
        """
        rerank_field_name = self._get_rerank_field_name()

        if self._query is None:
            raise ValueError(
                "query text is required for reranker, please specify it through "
                ".text('<your query string>')"
            )

        documents = [
            getattr(row._mapping[HIT_LABEL], rerank_field_name) for row in rows
        ]
        reranked_results = self._reranker.rerank(self._query, documents, self._limit)
        reranked_rows = []
        for item in reranked_results:
            row = rows[item.index]
            score_index = row._key_to_index[SCORE_LABEL]
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
                vector_field = self._table.auto_embedding_configs[
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
        _, rows = self._execute_query()
        results = []
        for row in rows:
            row_dict = dict(row._mapping)
            if HIT_LABEL in row_dict:
                hit = row_dict.pop(HIT_LABEL)
                if isinstance(hit, TableModel):
                    results.append(
                        {
                            **hit.model_dump(),
                            **row_dict,
                        }
                    )
                else:
                    raise ValueError(f"Unsupported search result type: {type(hit)}")
            else:
                results.append(row_dict)

        return results

    def to_pydantic(self, with_score: Optional[bool] = True) -> List[BaseModel]:
        _, rows = self._execute_query()
        results = []
        for row in rows:
            row_dict = dict(row._mapping)
            hit = row_dict.pop(HIT_LABEL)
            distance = (
                row_dict.pop(DISTANCE_LABEL) if DISTANCE_LABEL in row_dict else None
            )
            match_score = (
                row_dict.pop(MATCH_SCORE_LABEL)
                if MATCH_SCORE_LABEL in row_dict
                else None
            )
            score = row_dict.pop(SCORE_LABEL) if SCORE_LABEL in row_dict else None

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
        flatten_rows = []
        for row in rows:
            row_dict = dict(row._mapping)
            if HIT_LABEL in row_dict:
                hit = row_dict.pop(HIT_LABEL)
                flatten_rows.append((*hit.model_dump().values(), *row_dict.values()))
            else:
                flatten_rows.append(row_dict.values())

        if HIT_LABEL in keys:
            flatten_keys = [
                *self._table.table_model.model_fields.keys(),
                *[key for key in keys if key != HIT_LABEL],
            ]
        else:
            flatten_keys = keys
        return pd.DataFrame(flatten_rows, columns=flatten_keys)
