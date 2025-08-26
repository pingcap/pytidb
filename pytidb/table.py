from pathlib import Path
from typing import (
    Literal,
    Optional,
    List,
    Any,
    Dict,
    TypeVar,
    Type,
    Union,
    TYPE_CHECKING,
)
import warnings

from sqlalchemy import Engine, Table as SaTable
from sqlalchemy.orm import DeclarativeMeta
from sqlmodel import Session
from sqlmodel.main import SQLModelMetaclass
from typing_extensions import Generic

from pytidb.filters import Filters, build_filter_clauses
from pytidb.orm.indexes import FullTextIndex, VectorIndex, format_distance_expression
from pytidb.orm.sql import ddl
from pytidb.sql import select, update, delete
from pytidb.schema import (
    QueryBundle,
    TableModelMeta,
    VectorDataType,
    TableModel,
    ColumnInfo,
    DistanceMetric,
)
from pytidb.search import SearchType, Search
from pytidb.result import QueryResult, SQLModelQueryResult
from pytidb.utils import (
    check_text_column,
    check_vector_column,
    filter_text_columns,
    filter_vector_columns,
    get_index_type,
)

if TYPE_CHECKING:
    from pytidb import TiDBClient
    from PIL.Image import Image


T = TypeVar("T", bound=TableModel)


class Table(Generic[T]):
    def __init__(self, *, client: "TiDBClient", schema: Optional[Type[T]] = None):
        self._client = client
        self._db_engine = client.db_engine
        self._identifier_preparer = self._db_engine.dialect.identifier_preparer

        # Init table model.
        if (
            type(schema) is TableModelMeta
            or type(schema) is SQLModelMetaclass
            or type(schema) is DeclarativeMeta
        ):
            self._table_model = schema
            self._sa_metadata = schema.metadata
        else:
            raise TypeError(f"Invalid schema type: {type(schema)}")

        self._sa_table: SaTable = self._table_model.__table__
        self._columns = self._table_model.__table__.columns

        # Determine default vector column for vector search.
        self._default_vector_column = None
        self._vector_columns = filter_vector_columns(self._columns)
        if len(self._vector_columns) == 1:
            self._default_vector_column = self._vector_columns[0]

        # Determine default text column for fulltext search.
        self._default_text_column = None
        self._text_columns = filter_text_columns(self._columns)
        if len(self._text_columns) == 1:
            self._default_text_column = self._text_columns[0]

        # Setup auto embedding.
        if hasattr(schema, "__pydantic_fields__"):
            vector_fields = {}
            text_fields = {}

            for field_name, field_info in self._table_model.__pydantic_fields__.items():
                if field_info._attributes_set.get("field_type", None) == "vector":
                    vector_fields[field_name] = field_info
                elif field_info._attributes_set.get("field_type", None) == "text":
                    text_fields[field_name] = field_info

            if len(vector_fields) == 1 and self._default_vector_column is None:
                vector_field_name = list(vector_fields.keys())[0]
                self._default_vector_column = check_vector_column(
                    self._columns, vector_field_name
                )
            if len(text_fields) == 1 and self._default_text_column is None:
                text_field_name = list(text_fields.keys())[0]
                self._default_text_column = check_text_column(
                    self._columns, text_field_name
                )

            self._setup_auto_embedding(vector_fields)
            self._auto_create_vector_index(vector_fields)
            self._auto_create_fulltext_index(text_fields)

    @property
    def table_model(self) -> T:
        return self._table_model

    @property
    def table_name(self) -> str:
        return self._table_model.__tablename__

    @property
    def client(self) -> "TiDBClient":
        return self._client

    @property
    def db_engine(self) -> Engine:
        return self._db_engine

    @property
    def vector_columns(self):
        return self._vector_columns

    @property
    def text_columns(self):
        return self._text_columns

    @property
    def auto_embedding_configs(self):
        return self._auto_embedding_configs

    def _setup_auto_embedding(self, vector_fields):
        """Setup auto embedding configurations for fields with embed_fn."""
        self._auto_embedding_configs = {}
        for vector_field_name, field in vector_fields.items():
            field_attrs = field._attributes_set
            embed_fn = field_attrs.get("embed_fn", None)
            if embed_fn is None:
                continue

            source_field_name = field_attrs.get("source_field", None)
            if source_field_name is None:
                continue

            source_type = field_attrs.get("source_type", "text")
            use_server = field_attrs.get("use_server", False)

            self._auto_embedding_configs[vector_field_name] = {
                "embed_fn": embed_fn,
                "vector_field": field,
                "vector_field_name": vector_field_name,
                "source_field_name": source_field_name,
                "source_type": source_type,
                "use_server": use_server,
            }

    def _auto_create_vector_index(self, vector_fields):
        for field_name, field in vector_fields.items():
            column_name = field_name
            skip_index = field._attributes_set.get("skip_index", False)
            if skip_index:
                continue

            distance_metric = field._attributes_set.get(
                "distance_metric", DistanceMetric.COSINE
            )
            algorithm = field._attributes_set.get("algorithm", "HNSW")

            # Check if the metric on the column is already defined in vector indexes
            distance_expression = format_distance_expression(
                column_name, distance_metric
            )
            indexed_expressions = [
                index.expressions[0].text
                for index in self._sa_table.indexes
                if get_index_type(index) == "vector"
            ]
            if distance_expression in indexed_expressions:
                continue

            # Create vector index automatically, if not defined
            self._sa_table.append_constraint(
                VectorIndex(
                    f"vec_idx_{column_name}_{distance_metric.lower()}",
                    column_name,
                    distance_metric=distance_metric,
                    algorithm=algorithm,
                )
            )

    def _auto_create_fulltext_index(self, text_fields):
        for text_field_name, field in text_fields.items():
            skip_index = field._attributes_set.get("skip_index", False)
            if skip_index:
                continue

            # Check if the column is already defined a fulltext index.
            column_name = text_field_name
            indexed_columns = [
                index.columns[0].name
                for index in self._sa_table.indexes
                if get_index_type(index) == "fulltext"
            ]
            if column_name in indexed_columns:
                continue

            # Create fulltext index automatically, if not defined
            fts_parser = field._attributes_set.get("fts_parser", "MULTILINGUAL")
            self._sa_table.append_constraint(
                FullTextIndex(
                    f"fts_idx_{column_name}",
                    column_name,
                    fts_parser=fts_parser,
                )
            )

    def create(self, if_exists: Literal["raise", "skip"] = "raise") -> "Table":
        checkfirst = if_exists == "skip"
        self.db_engine._run_ddl_visitor(
            ddl.TiDBSchemaGenerator, self._sa_table, checkfirst=checkfirst
        )
        return self

    def drop(self, if_not_exists: Literal["raise", "skip"] = "raise"):
        checkfirst = if_not_exists == "skip"
        self._sa_table.drop(self.db_engine, checkfirst=checkfirst)

    def get(self, id: Any) -> T:
        with self._client.session() as db_session:
            return db_session.get(self._table_model, id)

    def insert(self, data: Union[T, dict]) -> T:
        if not isinstance(data, self._table_model) and not isinstance(data, dict):
            raise ValueError(
                f"Invalid data type: {type(data)}, expected {self._table_model}, dict"
            )

        # Convert dict to table model instance.
        if isinstance(data, dict):
            data = self._table_model(**data)

        # Auto embedding.
        for field_name, config in self._auto_embedding_configs.items():
            # Skip if auto embedding in SQL is enabled, it will be handled in the database side.
            use_server = config.get("use_server", False)
            if use_server:
                continue

            # Skip if vector embeddings is provided.
            if getattr(data, field_name) is not None:
                continue

            # Skip if source field is not provided.
            if not hasattr(data, config["source_field_name"]):
                continue

            # Skip if source field is None or empty.
            embedding_source = getattr(data, config["source_field_name"])
            if embedding_source is None or embedding_source == "":
                setattr(data, field_name, None)
                continue

            source_type = config.get("source_type", "text")
            vector_embedding = config["embed_fn"].get_source_embedding(
                embedding_source,
                source_type=source_type,
            )
            setattr(data, field_name, vector_embedding)

        with self._client.session() as db_session:
            db_session.add(data)
            db_session.flush()
            db_session.refresh(data)
            return data

    def save(self, data: Union[T, dict]) -> T:
        if not isinstance(data, self._table_model) and not isinstance(data, dict):
            raise ValueError(
                f"Invalid data type: {type(data)}, expected {self._table_model}, dict"
            )

        # Convert dict to table model instance.
        if isinstance(data, dict):
            data = self._table_model(**data)

        # Auto embedding.
        for field_name, config in self._auto_embedding_configs.items():
            # Skip if auto embedding in SQL is enabled, it will be handled in the database side.
            use_server = config.get("use_server", False)
            if use_server:
                continue

            # Skip if vector embeddings is provided.
            if getattr(data, field_name) is not None:
                continue

            # Skip if source field is not provided.
            if not hasattr(data, config["source_field_name"]):
                continue

            # Skip if source field is None or empty.
            embedding_source = getattr(data, config["source_field_name"])
            if embedding_source is None or embedding_source == "":
                setattr(data, field_name, None)
                continue

            source_type = config.get("source_type", "text")
            vector_embedding = config["embed_fn"].get_source_embedding(
                embedding_source,
                source_type=source_type,
            )
            setattr(data, field_name, vector_embedding)

        with self._client.session() as db_session:
            merged_data = db_session.merge(data)
            db_session.flush()
            db_session.refresh(merged_data)
            return merged_data

    def bulk_insert(self, data: List[Union[T, dict]]) -> List[T]:
        if not isinstance(data, list):
            raise ValueError(
                f"Invalid data type: {type(data)}, expected list[dict], list[{self._table_model}]"
            )

        # Convert dict items to table model instances.
        data = [
            self._table_model(**item) if isinstance(item, dict) else item
            for item in data
        ]

        # Auto embedding.
        for field_name, config in self._auto_embedding_configs.items():
            items_need_embedding = []
            sources_to_embedding = []

            # Skip if auto embedding in SQL is enabled, it will be handled in the database side.
            use_server = config.get("use_server", False)
            if use_server:
                continue

            # Skip if no embedding function is provided.
            if "embed_fn" not in config or config["embed_fn"] is None:
                continue

            for item in data:
                # Skip if vector embeddings is provided.
                if getattr(item, field_name) is not None:
                    continue

                # Skip if no source field is provided.
                if not hasattr(item, config["source_field_name"]):
                    continue

                # Skip if source field is None or empty.
                embedding_source = getattr(item, config["source_field_name"])
                if embedding_source is None or embedding_source == "":
                    continue

                items_need_embedding.append(item)
                sources_to_embedding.append(embedding_source)

            # Batch embedding.
            source_type = config.get("source_type", "text")
            vector_embeddings = config["embed_fn"].get_source_embeddings(
                sources_to_embedding,
                source_type=source_type,
            )

            for item, embedding in zip(items_need_embedding, vector_embeddings):
                setattr(item, field_name, embedding)

        with self._client.session() as db_session:
            db_session.add_all(data)
            db_session.flush()
            for item in data:
                db_session.refresh(item)
            return data

    def update(self, values: dict, filters: Optional[Filters] = None) -> object:
        # Auto embedding.
        for field_name, config in self._auto_embedding_configs.items():
            # Skip if auto embedding in SQL is enabled, it will be handled in the database side.
            use_server = config.get("use_server", False)
            if use_server:
                continue

            # Skip if vector embeddings is provided.
            if field_name in values:
                continue

            # Skip if source field is not provided.
            if config["source_field_name"] not in values:
                continue

            # Skip if source field is None or empty.
            embedding_source = values[config["source_field_name"]]
            if embedding_source is None or embedding_source == "":
                values[field_name] = None
                continue

            source_type = config.get("source_type", "text")
            vector_embedding = config["embed_fn"].get_source_embedding(
                embedding_source,
                source_type=source_type,
            )
            values[field_name] = vector_embedding

        with self._client.session() as db_session:
            filter_clauses = build_filter_clauses(filters, self._sa_table)
            stmt = update(self._table_model).filter(*filter_clauses).values(values)
            db_session.execute(stmt)

    def delete(self, filters: Optional[Filters] = None):
        """
        Delete data from the TiDB table.

        params:
            filters: (Optional[Dict[str, Any]]): The filters to apply to the delete operation.
        """
        with self._client.session() as db_session:
            filter_clauses = build_filter_clauses(filters, self._sa_table)
            stmt = delete(self._table_model).filter(*filter_clauses)
            db_session.execute(stmt)

    def truncate(self):
        with self._client.session():
            table_name = self._identifier_preparer.quote(self.table_name)
            stmt = f"TRUNCATE TABLE {table_name};"
            self._client.execute(stmt)

    def columns(self) -> List[ColumnInfo]:
        with self._client.session():
            table_name = self._identifier_preparer.quote(self.table_name)
            stmt = """
                SELECT
                    COLUMN_NAME as column_name,
                    COLUMN_TYPE as column_type
                FROM INFORMATION_SCHEMA.COLUMNS
                WHERE
                    TABLE_SCHEMA = DATABASE()
                    AND TABLE_NAME = :table_name;
            """
            res = self._client.query(stmt, {"table_name": table_name})
            return res.to_pydantic(ColumnInfo)

    def rows(self):
        with self._client.session():
            table_name = self._identifier_preparer.quote(self.table_name)
            stmt = f"SELECT COUNT(*) FROM {table_name};"
            return self._client.query(stmt).scalar()

    def query(
        self,
        filters: Optional[Filters] = None,
        order_by: Optional[List[Any] | str | Dict[str, Any]] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
    ) -> QueryResult:
        with Session(self._db_engine) as db_session:
            stmt = select(self._table_model)

            # Apply filters.
            if filters is not None:
                filter_clauses = build_filter_clauses(filters, self._sa_table)
                stmt = stmt.filter(*filter_clauses)

            # Apply order by.
            if isinstance(order_by, list):
                stmt = stmt.order_by(*order_by)
            elif isinstance(order_by, str):
                if order_by not in self._columns:
                    raise KeyError(f"Unknown order by column: {order_by}")
                stmt = stmt.order_by(self._columns[order_by])
            elif isinstance(order_by, dict):
                for key, value in order_by.items():
                    if key not in self._columns:
                        raise KeyError(f"Unknown order by column: {key}")

                    if value == "desc":
                        stmt = stmt.order_by(self._columns[key].desc())
                    elif value == "asc":
                        stmt = stmt.order_by(self._columns[key])
                    else:
                        raise ValueError(
                            f"Invalid order direction value (allowed: 'desc', 'asc'): {value}"
                        )

            # Pagination.
            if limit is not None:
                stmt = stmt.limit(limit)
            if offset is not None:
                stmt = stmt.offset(offset)

            result = db_session.exec(stmt).all()
            return SQLModelQueryResult(result)

    def search(
        self,
        query: Optional[Union[VectorDataType, str, QueryBundle, "Image", Path]] = None,
        search_type: SearchType = "vector",
    ) -> Search:
        return Search(
            table=self,
            query=query,
            search_type=search_type,
        )

    def _has_tiflash_index(
        self,
        column_name: str,
        index_kind: Optional[Literal["FullText", "Vector"]] = None,
    ) -> bool:
        stmt = """SELECT EXISTS(
            SELECT 1
            FROM INFORMATION_SCHEMA.TIFLASH_INDEXES
            WHERE
                TIDB_DATABASE = DATABASE()
                AND TIDB_TABLE = :table_name
                AND COLUMN_NAME = :column_name
                AND INDEX_KIND = :index_kind
        )
        """
        with self._client.session():
            res = self._client.query(
                stmt,
                {
                    "table_name": self.table_name,
                    "column_name": column_name,
                    "index_kind": index_kind,
                },
            )
            return res.scalar()

    def _has_tidb_index(
        self, column_name: str, index_type: Optional[str] = None
    ) -> bool:
        table_name = self._identifier_preparer.quote(self.table_name)
        stmt = f"SHOW INDEXES FROM {table_name} WHERE Column_name = :column_name"
        params = {"column_name": column_name}

        if index_type is not None:
            stmt += " AND Index_type = :index_type"
            params["index_type"] = index_type

        with self._client.session():
            res = self._client.query(stmt, params)
            return len(res.to_list()) > 0

    def has_vector_index(self, column_name: str) -> bool:
        if self._client._is_serverless:
            return self._has_tiflash_index(column_name, "Vector")
        else:
            return self._has_tidb_index(column_name, "HNSW")

    def has_fts_index(self, column_name: str) -> bool:
        return self._has_tiflash_index(column_name, "FullText")

    def create_vector_index(
        self, column_name: str, name: Optional[str] = None, **kwargs
    ):
        # TODO: Support if_exists.
        warnings.warn(
            "table.create_vector_index() is an experimental API, use VectorField instead."
        )
        index_name = name or f"vec_idx_{column_name}"
        vec_idx = VectorIndex(index_name, self._columns[column_name], **kwargs)
        vec_idx.create(self.client.db_engine)

    def create_fts_index(
        self,
        column_name: str,
        name: Optional[str] = None,
        if_exists: Optional[Literal["raise", "skip"]] = "raise",
    ):
        warnings.warn(
            "table.create_fts_index() is an experimental API, use FullTextField instead."
        )
        index_name = name or f"fts_idx_{column_name}"
        fts_idx = FullTextIndex(index_name, self._columns[column_name])
        fts_idx.create(self.client.db_engine, checkfirst=(if_exists == "skip"))
