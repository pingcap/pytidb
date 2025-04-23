from typing import (
    Optional,
    List,
    Any,
    Dict,
    TypeVar,
    Type,
    Union,
    TYPE_CHECKING,
)

import sqlalchemy
from sqlalchemy import Engine, update, text
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
        Base.metadata.create_all(
            self._db_engine, tables=[self._table_model.__table__], checkfirst=checkfirst
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
        with self._client.session() as session:
            return session.get(self._table_model, id)

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

        with self._client.session() as session:
            session.add(data)
            session.flush()
            session.refresh(data)
            return data

    def bulk_insert(self, data: List[T]) -> List[T]:
        # Auto embedding.
        for field_name, config in self._vector_field_configs.items():
            items_need_embedding = []
            sources_to_embedding = []
            for item in data:
                if getattr(item, field_name) is not None:
                    continue
                if not hasattr(item, config["source_field_name"]):
                    continue
                items_need_embedding.append(item)
                embedding_source = getattr(item, config["source_field_name"])
                sources_to_embedding.append(embedding_source)

            vector_embeddings = config["embed_fn"].get_source_embeddings(
                sources_to_embedding
            )
            for item, embedding in zip(items_need_embedding, vector_embeddings):
                setattr(item, field_name, embedding)

        with self._client.session() as session:
            session.add_all(data)
            session.flush()
            for item in data:
                session.refresh(item)
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

        filter_clauses = build_filter_clauses(filters, self._columns, self._table_model)
        with self._client.session() as session:
            stmt = update(self._table_model).filter(*filter_clauses).values(values)
            session.execute(stmt)

    def delete(self, filters: Optional[Dict[str, Any]] = None):
        """
        Delete data from the TiDB table.

        params:
            filters: (Optional[Dict[str, Any]]): The filters to apply to the delete operation.
        """
        filter_clauses = build_filter_clauses(filters, self._columns, self._table_model)
        with self._client.session() as session:
            stmt = sqlalchemy.delete(self._table_model).filter(*filter_clauses)
            session.execute(stmt)
            session.commit()

    def truncate(self):
        with self._client.session() as session:
            table_name = self._db_engine.dialect.identifier_preparer.quote(
                self.table_name
            )
            session.execute(text(f"TRUNCATE TABLE {table_name};"))

    def columns(self) -> List[ColumnInfo]:
        show_columns_sql = text("""
            SELECT
                COLUMN_NAME,
                COLUMN_TYPE
            FROM information_schema.columns
            WHERE
                table_schema = DATABASE()
                AND table_name = :table_name;
        """)
        with self._client.session() as session:
            rows = session.execute(show_columns_sql, {"table_name": self.table_name})
            return [ColumnInfo(column_name=row[0], column_type=row[1]) for row in rows]

    def rows(self):
        with self._client.session() as session:
            table_name = self._db_engine.dialect.identifier_preparer.quote(
                self.table_name
            )
            res = session.execute(text(f"SELECT COUNT(*) FROM {table_name};"))
            return res.scalar()

    def query(self, filters: Optional[Dict[str, Any]] = None) -> List[T]:
        with Session(self._db_engine) as session:
            query = session.query(self._table_model)
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

    def _has_index(self, column_name: str) -> bool:
        table_name = self._table_model.__tablename__
        show_indexes_stmt = text("""
        SELECT *
        FROM INFORMATION_SCHEMA.TIDB_INDEXES
        WHERE
            TABLE_SCHEMA = DATABASE()
            AND TABLE_NAME = :table_name
            AND COLUMN_NAME = :column_name
        """)
        rows = self._client.query(
            show_indexes_stmt, {"table_name": table_name, "column_name": column_name}
        ).to_list()
        return len(rows) > 0

    def has_fts_index(self, column_name: str) -> bool:
        check_text_column(self._columns, column_name)
        # TODO: need to check if the index is a fulltext index.
        return self._has_index(column_name)

    def create_fts_index(self, column_name: str, name: Optional[str] = None) -> bool:
        table = self._table_model.__table__
        column = self._columns[column_name]
        preparer = self._db_engine.dialect.identifier_preparer

        if name is not None:
            _name = preparer.quote(name)
        else:
            _name = preparer.quote(f"fts_idx_{column_name}")
        _table_name = preparer.format_table(table)
        _column_name = preparer.format_column(column)

        add_tiflash_replica_stmt = f"ALTER TABLE {_table_name} SET TIFLASH REPLICA 1;"
        self._client.execute(add_tiflash_replica_stmt, raise_error=True)

        create_index_stmt = f"CREATE FULLTEXT INDEX IF NOT EXISTS {_name} ON {_table_name} ({_column_name}) WITH PARSER MULTILINGUAL;"
        self._client.execute(create_index_stmt, raise_error=True)

        return True
