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

from sqlalchemy import Engine, delete, update
from sqlalchemy.orm import Session, DeclarativeMeta
from sqlmodel.main import SQLModelMetaclass
from tidb_vector.sqlalchemy import VectorAdaptor
from typing_extensions import Generic

from pytidb.base import Base
from pytidb.schema import (
    QueryBundle,
    VectorDataType,
    TableModel,
    DistanceMetric,
    ColumnInfo,
)
from pytidb.search import SearchType, SearchQuery
from pytidb.utils import (
    build_filter_clauses,
    check_text_column,
    check_vector_column,
    filter_text_columns,
    filter_vector_columns,
)

if TYPE_CHECKING:
    from pytidb import TiDBClient


T = TypeVar("T", bound=TableModel)


class Table(Generic[T]):
    def __init__(
        self,
        *,
        client: "TiDBClient",
        schema: Optional[Type[T]] = None,
        vector_column: Optional[str] = None,
        text_column: Optional[str] = None,
        distance_metric: Optional[DistanceMetric] = DistanceMetric.COSINE,
        checkfirst: bool = True,
    ):
        self._client = client
        self._db_engine = client.db_engine
        self._identifier_preparer = self._db_engine.dialect.identifier_preparer

        # Init table model.
        if type(schema) is SQLModelMetaclass:
            self._table_model = schema
        elif type(schema) is DeclarativeMeta:
            self._table_model = schema
        else:
            raise TypeError(f"Invalid schema type: {type(schema)}")
        self._columns = self._table_model.__table__.columns

        # Field for auto embedding.
        self._vector_field_configs = {}
        if hasattr(schema, "__pydantic_fields__"):
            for name, field in schema.__pydantic_fields__.items():
                # FIXME: using field custom attributes instead of it.
                if "embed_fn" in field._attributes_set:
                    embed_fn = field._attributes_set["embed_fn"]
                    source_field_name = field._attributes_set["source_field"]
                    self._vector_field_configs[name] = {
                        "embed_fn": embed_fn,
                        "vector_field": field,
                        "source_field_name": source_field_name,
                    }

        # Create table.
        self._sa_table = self._table_model.__table__
        Base.metadata.create_all(
            self._db_engine, tables=[self._sa_table], checkfirst=checkfirst
        )

        # Find vector and text columns.
        self._vector_columns = filter_vector_columns(self._columns)
        self._text_columns = filter_text_columns(self._columns)

        # Create vector index automatically.
        vector_adaptor = VectorAdaptor(self._db_engine)
        for col in self._vector_columns:
            if vector_adaptor.has_vector_index(col):
                continue
            vector_adaptor.create_vector_index(col, distance_metric)

        # Determine default vector column for vector search.
        if vector_column is not None:
            self._vector_column = check_vector_column(self._columns, vector_column)
        else:
            if len(self._vector_columns) == 1:
                self._vector_column = self._vector_columns[0]
            else:
                self._vector_column = None

        # Determine default text column for fulltext search.
        if text_column is not None:
            self._text_column = check_text_column(self._columns, text_column)
        else:
            if len(self._text_columns) == 1:
                self._text_column = self._text_columns[0]
            else:
                self._text_column = None

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
    def vector_column(self):
        return self._vector_column

    @property
    def vector_columns(self):
        return self._vector_columns

    @property
    def text_column(self):
        return self._text_column

    @property
    def text_columns(self):
        return self._text_columns

    @property
    def vector_field_configs(self):
        return self._vector_field_configs

    def get(self, id: Any) -> T:
        with self._client.session() as db_session:
            return db_session.get(self._table_model, id)

    def insert(self, data: T) -> T:
        # Auto embedding.
        for field_name, config in self._vector_field_configs.items():
            if getattr(data, field_name) is not None:
                # Vector embeddings is provided.
                continue

            if not hasattr(data, config["source_field_name"]):
                continue

            embedding_source = getattr(data, config["source_field_name"])
            vector_embedding = config["embed_fn"].get_source_embedding(embedding_source)
            setattr(data, field_name, vector_embedding)

        with self._client.session() as db_session:
            db_session.add(data)
            db_session.flush()
            db_session.refresh(data)
            return data

    def bulk_insert(self, data: List[T]) -> List[T]:
        # Auto embedding.
        for field_name, config in self._vector_field_configs.items():
            items_need_embedding = []
            sources_to_embedding = []

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

                items_need_embedding.append(item)
                embedding_source = getattr(item, config["source_field_name"])
                sources_to_embedding.append(embedding_source)

            # Batch embedding.
            vector_embeddings = config["embed_fn"].get_source_embeddings(
                sources_to_embedding
            )
            for item, embedding in zip(items_need_embedding, vector_embeddings):
                setattr(item, field_name, embedding)

        with self._client.session() as db_session:
            db_session.add_all(data)
            db_session.flush()
            for item in data:
                db_session.refresh(item)
            return data

    def update(self, values: dict, filters: Optional[Dict[str, Any]] = None) -> object:
        # Auto embedding.
        for field_name, config in self._vector_field_configs.items():
            if field_name in values:
                # Vector embeddings is provided.
                continue

            if config["source_field_name"] not in values:
                continue

            embedding_source = values[config["source_field_name"]]
            vector_embedding = config["embed_fn"].get_source_embedding(embedding_source)
            values[field_name] = vector_embedding

        with self._client.session() as db_session:
            filter_clauses = build_filter_clauses(
                filters, self._columns, self._table_model
            )
            stmt = update(self._table_model).filter(*filter_clauses).values(values)
            db_session.execute(stmt)

    def delete(self, filters: Optional[Dict[str, Any]] = None):
        """
        Delete data from the TiDB table.

        params:
            filters: (Optional[Dict[str, Any]]): The filters to apply to the delete operation.
        """
        with self._client.session() as db_session:
            filter_clauses = build_filter_clauses(
                filters, self._columns, self._table_model
            )
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

    def query(self, filters: Optional[Dict[str, Any]] = None) -> List[T]:
        with Session(self._db_engine) as db_session:
            query = db_session.query(self._table_model)
            if filters:
                filter_clauses = build_filter_clauses(
                    filters, self._columns, self._table_model
                )
                query = query.filter(*filter_clauses)
            return query.all()

    def search(
        self,
        query: Optional[Union[VectorDataType, str, QueryBundle]] = None,
        search_type: SearchType = "vector",
    ) -> SearchQuery:
        return SearchQuery(
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

    def has_fts_index(self, column_name: str) -> bool:
        return self._has_tiflash_index(column_name, "FullText")

    def create_fts_index(self, column_name: str, name: Optional[str] = None):
        _name = self._identifier_preparer.quote(name or f"fts_idx_{column_name}")
        _column_name = self._identifier_preparer.format_column(
            self._columns[column_name]
        )

        add_tiflash_replica_stmt = (
            f"ALTER TABLE {self.table_name} SET TIFLASH REPLICA 1;"
        )
        self._client.execute(add_tiflash_replica_stmt, raise_error=True)

        create_index_stmt = (
            f"CREATE FULLTEXT INDEX {_name} ON "
            f"{self.table_name} ({_column_name}) "
            f"WITH PARSER MULTILINGUAL;"
        )
        self._client.execute(create_index_stmt, raise_error=True)
