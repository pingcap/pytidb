from typing import Optional

import sqlalchemy

from pytidb.utils import build_tidb_dsn
from sqlmodel import SQLModel, Field, Relationship as SQLRelationship


def test_static_create_models():
    tidb_dsn = str(build_tidb_dsn())
    db_engine = sqlalchemy.create_engine(str(tidb_dsn))

    class Entity(SQLModel, table=True):
        __tablename__ = "entities_1111"
        id: Optional[int] = Field(default=None, primary_key=True)
        name: str = Field()

    class Relationship(SQLModel, table=True):
        __tablename__ = "relationships_1111"
        id: Optional[int] = Field(default=None, primary_key=True)
        desc: str = Field()
        target_entity_id: int = Field()
        target_entity: Entity = SQLRelationship(
            sa_relationship_kwargs={
                "primaryjoin": "Relationship.source_entity_id == Entity.id",
                "lazy": "joined",
            },
        )

    SQLModel.metadata.create_all(db_engine)


def test_dynamic_create_models():
    tidb_dsn = str(build_tidb_dsn())
    db_engine = sqlalchemy.create_engine(str(tidb_dsn))

    entity_table_name = "entities_2222"
    entity_model_name = f"EntityModel_{entity_table_name}"

    relationship_table_name = "relationships_2222"
    relationship_model_name = f"RelationshipModel_{relationship_table_name}"

    class Entity(SQLModel):
        id: Optional[int] = Field(default=None, primary_key=True)
        name: str = Field()

    entity_model = type(
        entity_model_name,
        (Entity,),
        {"__tablename__": entity_table_name},
        table=True,
    )

    class Relationship(SQLModel):
        id: Optional[int] = Field(default=None, primary_key=True)
        desc: str = Field()
        source_entity_id: int = Field(foreign_key=f"{entity_table_name}.id")

    type(
        relationship_model_name,
        (Relationship,),
        {
            "__tablename__": relationship_table_name,
            # Notice: In SQLModel rules, Relationship should be defined on the model class set to table=True.
            # If the definition is in the parent class, an error will occur.
            "__annotations__": {"target_entity": entity_model},
            "target_entity": SQLRelationship(
                sa_relationship_kwargs={
                    "primaryjoin": f"{relationship_model_name}.source_entity_id == {entity_model_name}.id",
                    "lazy": "joined",
                },
            ),
        },
        table=True,
    )

    SQLModel.metadata.create_all(db_engine)
