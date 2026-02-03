#!/usr/bin/env python3
import os
import random
from typing import Any, Dict, List, Optional, Tuple

import dotenv
import sqlparse
import streamlit as st
import pandas as pd

from pytidb import Table, TiDBClient
from pytidb.schema import TableModel, Field
from pytidb.embeddings import EmbeddingFunction
from pytidb.datatype import JSON

dotenv.load_dotenv()

# Initial data: 3000 rows, batch insert size (auto embedding from text)
NUM_ROWS = 3000
BATCH_SIZE = 300

LANGUAGES = ["english", "chinese", "japanese"]
WORD_POOL = [
    "data",
    "database",
    "vector",
    "search",
    "machine",
    "learning",
    "distributed",
    "cloud",
    "storage",
    "query",
    "index",
    "embedding",
    "model",
    "algorithm",
    "system",
    "service",
    "api",
    "network",
    "cache",
    "transaction",
]

st.set_page_config(
    page_title="Vector Index Demo",
    page_icon="🔍",
    layout="wide",
    initial_sidebar_state="expanded",
)

if "db" not in st.session_state:
    st.session_state.db = None
if "text_embed" not in st.session_state:
    st.session_state.text_embed = None
if "table" not in st.session_state:
    st.session_state.table = None
if "initial_data_loaded" not in st.session_state:
    st.session_state.initial_data_loaded = False


def connect_to_tidb() -> TiDBClient:
    try:
        db = TiDBClient.connect(
            host=os.getenv("TIDB_HOST", "localhost"),
            port=int(os.getenv("TIDB_PORT", "4000")),
            username=os.getenv("TIDB_USERNAME", "root"),
            password=os.getenv("TIDB_PASSWORD", ""),
            database=os.getenv("TIDB_DATABASE", "vector_index_example"),
            ensure_db=True,
        )
        if db.is_serverless:
            api_key = os.getenv("OPENAI_API_KEY")
            if api_key:
                db.configure_embedding_provider("openai", api_key)
        return db
    except Exception as e:
        st.error(f"Failed to connect to TiDB: {str(e)}")
        st.stop()
        raise


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
        raise


def _random_text(doc_id: int) -> str:
    n = random.randint(5, 15)
    words = random.choices(WORD_POOL, k=n)
    return f"Document {doc_id}: " + " ".join(words) + "."


def _generate_chunks(n: int, start_id: int = 1) -> List[Dict[str, Any]]:
    """Generate chunk dicts (id, text, meta). text_vec is filled by auto embedding."""
    chunks = []
    for i in range(n):
        doc_id = start_id + i
        chunks.append(
            {
                "id": doc_id,
                "text": _random_text(doc_id),
                "meta": {"language": random.choice(LANGUAGES)},
            }
        )
    return chunks


def load_initial_data(table: Table) -> None:
    """Load NUM_ROWS random chunks in batches with progress bar."""
    Chunk = table.table_model
    total_batches = (NUM_ROWS + BATCH_SIZE - 1) // BATCH_SIZE
    progress_bar = st.progress(
        0.0, text="Generating and embedding data (this may take a while)..."
    )
    try:
        for batch_idx in range(total_batches):
            start = batch_idx * BATCH_SIZE
            end = min(start + BATCH_SIZE, NUM_ROWS)
            batch_chunks = _generate_chunks(end - start, start_id=start + 1)
            rows = [Chunk(**c) for c in batch_chunks]
            table.bulk_insert(rows)
            progress_bar.progress(
                (batch_idx + 1) / total_batches,
                text=f"Embedding and saving rows {start + 1}–{end} of {NUM_ROWS}…",
            )
        progress_bar.empty()
    except Exception as e:
        progress_bar.empty()
        st.error(f"Failed to load initial data: {str(e)}")
        raise


def perform_search(
    table: Table,
    query_text: str,
    language: str,
    query_limit: int,
    distance_threshold: float,
) -> Tuple[List[Dict[str, Any]], Optional[str]]:
    """Run vector search and return (results, compiled_sql)."""
    try:
        search_query = (
            table.search(query_text)
            .debug(True)
            .distance_threshold(distance_threshold)
            .limit(query_limit)
        )
        if language != "all":
            search_query = search_query.filter({"meta.language": language})

        compiled_sql = search_query.compiled_vector_query_sql()
        results = search_query.to_list()
        return results, compiled_sql
    except Exception as e:
        st.error(f"Failed to perform vector search: {str(e)}")
        return [], None


def display_search_results(results: List[Dict[str, Any]], query_text: str) -> None:
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
    if "meta" in df.columns:
        df = df.drop(columns=["meta"])

    st.dataframe(df, hide_index=True)


def _format_sql(sql: str) -> str:
    """Format SQL for readable display."""
    return sqlparse.format(sql.strip(), reindent=True, keyword_case="upper")


def display_sql_and_plan(db: TiDBClient, compiled_sql: Optional[str]) -> None:
    if not compiled_sql or not compiled_sql.strip():
        return

    st.markdown("#### Executed SQL")
    st.code(_format_sql(compiled_sql), language="sql")

    st.markdown("#### TiDB execution plan (EXPLAIN ANALYZE)")
    try:
        explain_sql = "EXPLAIN ANALYZE " + compiled_sql.strip().rstrip(";")
        result = db.query(explain_sql)
        plan_rows = result.to_list()
        if plan_rows:
            plan_df = pd.DataFrame(plan_rows)
            column_config = {
                col: st.column_config.Column(width=None) for col in plan_df.columns
            }
            st.dataframe(
                plan_df,
                hide_index=True,
                column_config=column_config,
            )
        else:
            st.info("No plan rows returned.")
    except Exception as e:
        st.error(f"Failed to run EXPLAIN ANALYZE: {str(e)}")


def setup() -> None:
    if st.session_state.db is None:
        with st.spinner("Connecting to TiDB..."):
            st.session_state.db = connect_to_tidb()

    if st.session_state.text_embed is None:
        with st.spinner("Setting up embedding function..."):
            st.session_state.text_embed = EmbeddingFunction(
                model_name="openai/text-embedding-3-small",
                use_server=st.session_state.db.is_serverless,
                api_key=os.getenv("OPENAI_API_KEY") if not st.session_state.db.is_serverless else None,
            )

    db = st.session_state.db
    text_embed = st.session_state.text_embed
    if st.session_state.table is None:
        with st.spinner("Setting up vector table and building vector index..."):
            st.session_state.table = setup_table(db, text_embed)

    table = st.session_state.table
    if table.rows() == 0 and not st.session_state.initial_data_loaded:
        try:
            load_initial_data(table)
        except Exception:
            st.session_state.initial_data_loaded = True
            st.rerun()
        st.session_state.initial_data_loaded = True
        st.rerun()


def main() -> None:
    setup()

    with st.sidebar:
        st.logo(
            "../assets/logo-full.svg",
            size="large",
            link="https://pingcap.github.io/ai/",
        )

        st.markdown(
            """#### Overview

This demo runs **vector search** on **3,000** randomly generated text chunks.
After each search you can see the **executed SQL** and **EXPLAIN ANALYZE** plan.
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

        table = st.session_state.table
        if table is not None and table.vector_columns:
            vec_col = table.vector_columns[0]
            try:
                has_idx = table.has_vector_index(vec_col.name)
                st.markdown("#### Index status")
                if has_idx:
                    st.success(f"Vector index on `{vec_col.name}`: built")
                else:
                    st.warning(f"Vector index on `{vec_col.name}`: not built yet")
            except Exception:
                st.caption("Index status: unknown")

    st.markdown(
        '<h3 style="text-align: center; padding-top: 40px;">🔍 Vector Index Demo</h3>',
        unsafe_allow_html=True,
    )

    with st.form("search_form", clear_on_submit=False):
        col1, col2 = st.columns([6, 1])
        with col1:
            query_text = st.text_input(
                "Search Query:",
                placeholder="e.g. vector search, distributed database, machine learning",
                label_visibility="collapsed",
            )
        with col2:
            st.form_submit_button("Search", width=100)

    if not query_text.strip():
        st.markdown(
            '<p style="text-align: center;">Try: '
            "<b>vector search</b>, <b>distributed database</b>, <b>machine learning</b>, "
            "<b>cloud storage</b></p>",
            unsafe_allow_html=True,
        )
        return

    with st.spinner("Searching for similar chunks..."):
        table = st.session_state.table
        db = st.session_state.db
        results, compiled_sql = perform_search(
            table, query_text, filter_language, query_limit, distance_threshold
        )

    display_search_results(results, query_text)

    if compiled_sql:
        st.markdown("---")
        display_sql_and_plan(db, compiled_sql)


if __name__ == "__main__":
    main()
