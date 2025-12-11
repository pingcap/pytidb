from contextlib import contextmanager

from sqlalchemy.pool import StaticPool
from sqlmodel import SQLModel, Session, create_engine

from pytidb.table import Table
from pytidb.schema import TableModel, Field


class _FakeClient:
    def __init__(self, engine):
        self.db_engine = engine

    @contextmanager
    def session(self):
        session = Session(self.db_engine, expire_on_commit=False)
        try:
            yield session
            session.commit()
        finally:
            session.close()


def test_table_update_returns_updated_instance():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    class Sample(TableModel, table=True):
        __tablename__ = "test_table_update_returns_updated_instance"
        id: int = Field(primary_key=True)
        name: str = Field()
        counter: int = Field(default=0)

    SQLModel.metadata.create_all(engine)

    table = Table(client=_FakeClient(engine), schema=Sample)
    table.insert(Sample(id=1, name="old", counter=1))

    updated = table.update(
        values={"name": "new", "counter": 2},
        filters={"id": 1},
    )

    assert isinstance(updated, Sample)
    assert updated.id == 1
    assert updated.name == "new"
    assert updated.counter == 2
