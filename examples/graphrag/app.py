#!/usr/bin/env python3
import os
from typing import Any, List, Dict

import dotenv
import streamlit as st
import pandas as pd

from pytidb import Table, TiDBClient
from pytidb.schema import TableModel, Field, Relationship
from pytidb.embeddings import EmbeddingFunction
from pytidb.datatype import JSON, TEXT


# Load environment variables
dotenv.load_dotenv()

# Page configuration
st.set_page_config(
    page_title="Vector Search Demo",
    page_icon="🔍",
    layout="centered",
    initial_sidebar_state="expanded",
)

# Initialize session state
if "db" not in st.session_state:
    st.session_state.db = None
if "text_embed" not in st.session_state:
    st.session_state.text_embed = None
if "table" not in st.session_state:
    st.session_state.table = None


def connect_to_tidb() -> TiDBClient:
    try:
        db = TiDBClient.connect(
            host=os.getenv("TIDB_HOST", "localhost"),
            port=int(os.getenv("TIDB_PORT", "4000")),
            username=os.getenv("TIDB_USERNAME", "root"),
            password=os.getenv("TIDB_PASSWORD", ""),
            database=os.getenv("TIDB_DATABASE", "vector_search_example"),
            ensure_db=True,
        )
        return db
    except Exception as e:
        st.error(f"Failed to connect to TiDB: {str(e)}")
        st.stop()


def setup_graph_table(db: TiDBClient, text_embed: EmbeddingFunction) -> Table:
    try:
        entity_table = db.open_table("entities")
        if entity_table is None:

            class Entity(TableModel):
                __tablename__ = "entities"
                __table_args__ = {"extend_existing": True}

                id: int = Field(primary_key=True)
                name: str = Field()
                description: str = Field()
                embedding: list[float] = text_embed.VectorField(
                    source_field="name",
                )
                meta: dict = Field(sa_type=JSON, default_factory=dict)

            entity_table = db.create_table(schema=Entity, if_exists="skip")

        relation_table = db.open_table("relations")
        if relation_table is None:

            class Relation(TableModel):
                __tablename__ = "relations"
                __table_args__ = {"extend_existing": True}

                id: int = Field(primary_key=True)
                description: str = Field()
                source_entity_id: int = Field(foreign_key="entities.id")
                target_entity_id: int = Field(foreign_key="entities.id")
                triple_str: str = Field(sa_type=TEXT)
                embedding: list[float] = text_embed.VectorField(
                    source_field="triple_str",
                )
                meta: dict = Field(sa_type=JSON, default_factory=dict)
                source_entity: Entity = Relationship(
                    sa_relationship_kwargs={
                        "primaryjoin": "Relation.source_entity_id == Entity.id",
                        "lazy": "joined",
                    },
                )
                target_entity: Entity = Relationship(
                    sa_relationship_kwargs={
                        "primaryjoin": "Relation.target_entity_id == Entity.id",
                        "lazy": "joined",
                    },
                )

            relation_table = db.create_table(schema=Relation, if_exists="skip")
        return entity_table, relation_table
    except Exception as e:
        st.error(f"Failed to create graph tables: {str(e)}")
        st.stop()


def load_sample_data(
    entity_table: Table, relation_table: Table, text_embed: EmbeddingFunction
):
    Entity = entity_table.table_model
    Relation = relation_table.table_model

    sample_entities = [
        {
            "id": 1,
            "name": "TiKV",
            "description": "TiKV is a distributed key-value database.",
            "meta": {"language": "english"},
        },
        {
            "id": 2,
            "name": "Python",
            "description": "Python's GIL ensures only one thread executes bytecode at a time.",
            "meta": {"language": "english"},
        },
        {
            "id": 3,
            "name": "TiDB",
            "description": "TiDB is a distributed SQL database with HTAP capabilities.",
            "meta": {"language": "english"},
        },
    ]

    sample_relations = [
        {
            "id": 1,
            "description": "TiDB uses TiKV as its storage engine.",
            "source_entity_id": 1,
            "target_entity_id": 3,
            "triple_str": "TiDB -> TiDB uses TiKV as its storage engine. -> TiKV",
        },
        {
            "id": 2,
            "description": "TiDB provides Python SDK for developers to use.",
            "source_entity_id": 3,
            "target_entity_id": 2,
            "triple_str": "TiDB -> TiDB provides Python SDK for developers to use. -> Python",
        },
    ]

    try:
        with st.spinner(
            f"Loading sample entities and relations (embedding with model: {text_embed.model_name}), "
            "it may take a while..."
        ):
            entity_table.bulk_insert([Entity(**entity) for entity in sample_entities])
            relation_table.bulk_insert(
                [Relation(**relation) for relation in sample_relations]
            )
    except Exception as e:
        st.error(f"Failed to load sample data: {str(e)}")
        st.stop()


def perform_search(
    relation_table: Table,
    query_text: str,
    language: str,
    query_limit: int,
    distance_threshold: float,
) -> List[Dict[str, Any]]:
    try:
        search_query = relation_table.search(query_text).debug(True)
        if language != "all":
            search_query = search_query.filter({"meta.language": language})

        return (
            search_query.distance_threshold(distance_threshold)
            .limit(query_limit)
            .to_list()
        )
    except Exception as e:
        st.error(f"Failed to perform vector search: {str(e)}")
        return []


def display_search_results(results: List[Dict[str, Any]], query_text: str):
    if not results:
        st.info("No results found for your query.")
        return

    st.markdown(
        f'Found <b>{len(results)}</b> results for <b>"{query_text}"</b>',
        unsafe_allow_html=True,
    )

    df = pd.DataFrame(results)
    if "text_vec" in df.columns:
        df = df.drop(columns=["text_vec"])
        df = df.drop(columns=["meta"])

    st.dataframe(df, hide_index=True)


def setup():
    # Initialize database and table
    if st.session_state.db is None:
        with st.spinner("Connecting to TiDB..."):
            db = connect_to_tidb()
            st.session_state.db = db

    # Setup embedding function
    if st.session_state.text_embed is None:
        with st.spinner("Setting up embedding function..."):
            text_embed = EmbeddingFunction(
                model_name="tidbcloud_free/cohere/embed-multilingual-v3",
            )
            st.session_state.text_embed = text_embed

    # Setup table
    if st.session_state.entity_table is None or st.session_state.relation_table is None:
        with st.spinner("Setting up graph tables..."):
            entity_table, relation_table = setup_graph_table(db, text_embed)
            st.session_state.entity_table = entity_table
            st.session_state.relation_table = relation_table

    # Load sample data if table is empty
    if entity_table.rows() == 0:
        load_sample_data(entity_table, relation_table, text_embed)
        st.rerun()


def main():
    # Sidebar
    with st.sidebar:
        st.logo(
            "../assets/logo-full.svg",
            size="large",
            link="https://pingcap.github.io/ai/",
        )

        st.markdown(
            """#### Overview

**Vector search** offers a powerful solution for **semantic similarity** searches across
diverse data types, such as documents, images, audio, and video.
            """
        )

        st.markdown("#### Settings")
        filter_language = st.selectbox(
            "Language",
            ["all", "english", "chinese", "japanese"],
            index=0,
            help="Filter results by language",
        )
        query_limit = st.slider(
            "Query limit",
            min_value=1,
            max_value=20,
            value=5,
            help="Maximum number of results to return",
        )
        distance_threshold = st.slider(
            "Distance threshold",
            min_value=0.0,
            max_value=1.0,
            value=0.6,
            step=0.01,
            help="Set the maximum distance for similarity",
        )

    # Main content
    setup()

    st.markdown(
        '<h3 style="text-align: center; padding-top: 40px;">🔍 Vector Search Demo</h3>',
        unsafe_allow_html=True,
    )

    with st.form("search_form", clear_on_submit=False):
        col1, col2 = st.columns([6, 1])
        with col1:
            query_text = st.text_input(
                "Search Query:",
                placeholder="Enter your search query",
                label_visibility="collapsed",
            )
        with col2:
            st.form_submit_button("Search", width=100)

    if not query_text.strip():
        st.markdown(
            '<p style="text-align: center;">Try searching for: '
            '<b>"HTAP database"</b>, <b>"machine learning"</b>'
            "</p>",
            unsafe_allow_html=True,
        )
        return

    with st.spinner("Searching for similar chunks..."):
        relation_table = st.session_state.relation_table
        results = perform_search(
            relation_table, query_text, filter_language, query_limit, distance_threshold
        )
        display_search_results(results, query_text)


if __name__ == "__main__":
    main()
