from typing import Optional


from pytidb.client import TiDBClient
from sqlmodel import SQLModel, Field, Relationship as SQLRelationship


def test_static_create_models(shared_client: TiDBClient):
    class Entity(SQLModel, table=True):
        __tablename__ = "entities_1111"
        id: Optional[int] = Field(default=None, primary_key=True)
        name: str = Field()

    class Relation(SQLModel, table=True):
        __tablename__ = "relations_1111"
        id: Optional[int] = Field(default=None, primary_key=True)
        desc: str = Field()
        target_entity_id: int = Field(foreign_key="entities_1111.id")
        target_entity: Entity = SQLRelationship(
            sa_relationship_kwargs={
                "primaryjoin": "Relation.target_entity_id == Entity.id",
                "lazy": "joined",
            },
        )

    SQLModel.metadata.create_all(
        shared_client.db_engine,
        [
            Entity.__table__,
            Relation.__table__,
        ],
    )


def test_dynamic_create_models(shared_client: TiDBClient):
    entity_table_name = "entities_2222"
    entity_model_name = f"EntityModel_{entity_table_name}"

    relation_table_name = "relations_2222"
    relation_model_name = f"RelationModel_{relation_table_name}"

    class Entity(SQLModel):
        id: Optional[int] = Field(default=None, primary_key=True)
        name: str = Field()

    entity_model = type(
        entity_model_name,
        (Entity,),
        {"__tablename__": entity_table_name},
        table=True,
    )

    class Relation(SQLModel):
        id: Optional[int] = Field(default=None, primary_key=True)
        desc: str = Field()
        source_entity_id: int = Field(foreign_key=f"{entity_table_name}.id")

    relation_model = type(
        relation_model_name,
        (Relation,),
        {
            "__tablename__": relation_table_name,
            # Notice: In SQLModel rules, Relationship should be defined on the model class set to table=True.
            # If the definition is in the parent class, an error will occur.
            "__annotations__": {"target_entity": entity_model},
            "target_entity": SQLRelationship(
                sa_relationship_kwargs={
                    "primaryjoin": f"{relation_model_name}.source_entity_id == {entity_model_name}.id",
                    "lazy": "joined",
                },
            ),
        },
        table=True,
    )

    SQLModel.metadata.create_all(
        shared_client.db_engine,
        [
            entity_model.__table__,
            relation_model.__table__,
        ],
    )
