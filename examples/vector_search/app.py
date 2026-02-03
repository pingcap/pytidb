#!/usr/bin/env python3
import os
from typing import Any, List, Dict

import dotenv
import streamlit as st
import pandas as pd

from pytidb import Table, TiDBClient
from pytidb.schema import TableModel, Field
from pytidb.embeddings import EmbeddingFunction
from pytidb.datatype import JSON


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
if "sample_data_loaded" not in st.session_state:
    st.session_state.sample_data_loaded = False


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


def setup_table(db: TiDBClient, text_embed: EmbeddingFunction) -> Table:
    try:
        table = db.open_table("chunks")
        if table is None:

            class Chunk(TableModel):
                __tablename__ = "chunks"
                __table_args__ = {"extend_existing": True}

                id: int = Field(primary_key=True)
                text: str = Field()
                text_vec: list[float] = text_embed.VectorField(
                    source_field="text",
                )
                meta: dict = Field(sa_type=JSON)

            table = db.create_table(schema=Chunk, if_exists="overwrite")
        return table
    except Exception as e:
        st.error(f"Failed to create table: {str(e)}")
        st.stop()


def load_sample_data(table: Table, text_embed: EmbeddingFunction) -> None:
    """Load sample chunks with explicit ids to avoid duplicate inserts across tabs/reruns."""
    sample_chunks = [
        {"id": 1, "text": "Llamas are camelids known for their soft fur and use as pack animals.", "meta": {"language": "english"}},
        {"id": 2, "text": "Python's GIL ensures only one thread executes bytecode at a time.", "meta": {"language": "english"}},
        {"id": 3, "text": "TiDB is a distributed SQL database with HTAP capabilities.", "meta": {"language": "english"}},
        {"id": 4, "text": "TiDB是一个开源的NewSQL数据库，支持混合事务和分析处理（HTAP）工作负载。", "meta": {"language": "chinese"}},
        {"id": 5, "text": "TiDBはオープンソースの分散型HTAPデータベースで、トランザクション処理と分析処理の両方をサポートしています。", "meta": {"language": "japanese"}},
        {"id": 6, "text": "Einstein's theory of relativity revolutionized modern physics.", "meta": {"language": "english"}},
        {"id": 7, "text": "The Great Wall of China stretches over 13,000 miles.", "meta": {"language": "english"}},
        {"id": 8, "text": "Ollama enables local deployment of large language models.", "meta": {"language": "english"}},
        {"id": 9, "text": "HTTP/3 uses QUIC protocol for improved web performance.", "meta": {"language": "english"}},
        {"id": 10, "text": "Kubernetes orchestrates containerized applications across clusters.", "meta": {"language": "english"}},
        {"id": 11, "text": "Blockchain technology enables decentralized transaction systems.", "meta": {"language": "english"}},
        {"id": 12, "text": "GPT-4 demonstrates remarkable few-shot learning capabilities.", "meta": {"language": "english"}},
        {"id": 13, "text": "Machine learning algorithms improve with more training data.", "meta": {"language": "english"}},
        {"id": 14, "text": "Quantum computing uses qubits instead of traditional bits.", "meta": {"language": "english"}},
        {"id": 15, "text": "Neural networks are inspired by the human brain's structure.", "meta": {"language": "english"}},
        {"id": 16, "text": "Docker containers package applications with their dependencies.", "meta": {"language": "english"}},
        {"id": 17, "text": "Cloud computing provides on-demand computing resources.", "meta": {"language": "english"}},
        {"id": 18, "text": "Artificial intelligence aims to mimic human cognitive functions.", "meta": {"language": "english"}},
        {"id": 19, "text": "Cybersecurity protects systems from digital attacks.", "meta": {"language": "english"}},
        {"id": 20, "text": "Big data analytics extracts insights from large datasets.", "meta": {"language": "english"}},
        {"id": 21, "text": "Internet of Things connects everyday objects to the internet.", "meta": {"language": "english"}},
        {"id": 22, "text": "Augmented reality overlays digital content on the real world.", "meta": {"language": "english"}},
    ]

    try:
        with st.spinner(
            f"Loading sample chunks (embedding with model: `{text_embed.model_name}`), "
            "it may take a while..."
        ):
            Chunk = table.table_model
            table.bulk_insert([Chunk(**chunk) for chunk in sample_chunks])
    except Exception as e:
        st.error(f"Failed to load sample data: {str(e)}")
        raise


def perform_search(
    table, query_text: str, language: str, query_limit: int, distance_threshold: float
) -> List[Dict[str, Any]]:
    try:
        search_query = table.search(query_text).debug(True)
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
            st.session_state.db = connect_to_tidb()

    # Setup embedding function
    if st.session_state.text_embed is None:
        with st.spinner("Setting up embedding function..."):
            st.session_state.text_embed = EmbeddingFunction(
                model_name="tidbcloud_free/cohere/embed-multilingual-v3",
            )

    # Setup table
    db = st.session_state.db
    text_embed = st.session_state.text_embed
    if st.session_state.table is None:
        with st.spinner("Setting up vector table..."):
            st.session_state.table = setup_table(db, text_embed)

    # Load sample data at most once per session when table is empty (avoids duplicate
    # inserts from multiple tabs or reruns where rows() is still 0 before first commit).
    table = st.session_state.table
    if table.rows() == 0 and not st.session_state.sample_data_loaded:
        try:
            load_sample_data(table, text_embed)
        except Exception:
            # e.g. duplicate key when another tab already loaded; mark loaded and rerun
            st.session_state.sample_data_loaded = True
            st.rerun()
        st.session_state.sample_data_loaded = True
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
            '<b>"distributed mysql"</b>, <b>"machine learning"</b>'
            "</p>",
            unsafe_allow_html=True,
        )
        return

    with st.spinner("Searching for similar chunks..."):
        table = st.session_state.table
        results = perform_search(
            table, query_text, filter_language, query_limit, distance_threshold
        )
        display_search_results(results, query_text)


if __name__ == "__main__":
    main()
