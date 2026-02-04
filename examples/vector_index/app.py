#!/usr/bin/env python3
import os
import random
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any, Dict, List, Optional, Tuple

import dotenv
import sqlparse
import streamlit as st
import pandas as pd

from pytidb import Table, TiDBClient
from pytidb.schema import TableModel, Field, Column
from pytidb.orm.indexes import VectorIndex
from pytidb.orm.tiflash_replica import TiFlashReplica
from pytidb.datatype import VECTOR

dotenv.load_dotenv()

# 3-dim random vectors, no auto embedding
VECTOR_DIM = 3
NUM_ROWS = 6000
BATCH_SIZE = 300
INSERT_WORKERS = 6

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
if "table" not in st.session_state:
    st.session_state.table = None
if "initial_data_loaded" not in st.session_state:
    st.session_state.initial_data_loaded = False
if "pending_search_vector" not in st.session_state:
    st.session_state.pending_search_vector = None


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
        return db
    except Exception as e:
        st.error(f"Failed to connect to TiDB: {str(e)}")
        st.stop()
        raise


def setup_table(db: TiDBClient) -> Table:
    try:
        table = db.open_table("chunks")
        if table is None:

            class Chunk(TableModel):
                __tablename__ = "chunks"
                __table_args__ = (
                    VectorIndex("vec_idx_text_vec_cosine", "text_vec"),
                    {"extend_existing": True},
                )

                id: int = Field(primary_key=True)
                text: str = Field()
                text_vec: list[float] = Field(sa_column=Column(VECTOR(VECTOR_DIM)))

            table = db.create_table(schema=Chunk, if_exists="overwrite")
        return table
    except Exception as e:
        st.error(f"Failed to create table: {str(e)}")
        st.stop()
        raise


def _random_vector(dim: int) -> list[float]:
    vec = [random.gauss(0, 1) for _ in range(dim)]
    norm = (sum(x * x for x in vec)) ** 0.5
    if norm == 0:
        return [1.0 / dim] * dim
    return [round(x / norm, 6) for x in vec]


def _random_text(doc_id: int) -> str:
    n = random.randint(5, 15)
    words = random.choices(WORD_POOL, k=n)
    return f"Document {doc_id}: " + " ".join(words) + "."


def _generate_chunks(n: int, start_id: int = 1) -> List[Dict[str, Any]]:
    """Generate chunk dicts (id, text, text_vec) with random 3-dim vectors."""
    chunks = []
    for i in range(n):
        doc_id = start_id + i
        chunks.append(
            {
                "id": doc_id,
                "text": _random_text(doc_id),
                "text_vec": _random_vector(VECTOR_DIM),
            }
        )
    return chunks


def _insert_batch(table: Table, start: int, count: int) -> None:
    """Generate one batch of chunks and bulk_insert (for concurrent workers)."""
    Chunk = table.table_model
    batch_chunks = _generate_chunks(count, start_id=start)
    rows = [Chunk(**c) for c in batch_chunks]
    table.bulk_insert(rows)


def load_initial_data(table: Table) -> None:
    """Load NUM_ROWS random chunks (3-dim vectors) with 6 concurrent insert workers."""
    total_batches = (NUM_ROWS + BATCH_SIZE - 1) // BATCH_SIZE
    progress_bar = st.progress(0.0, text="Ingesting sample data …")
    try:
        done = 0
        with ThreadPoolExecutor(max_workers=INSERT_WORKERS) as executor:
            futures = {}
            for batch_idx in range(total_batches):
                start = batch_idx * BATCH_SIZE
                count = min(BATCH_SIZE, NUM_ROWS - start)
                future = executor.submit(_insert_batch, table, start + 1, count)
                futures[future] = (start, count)
            for future in as_completed(futures):
                future.result()
                done += 1
                progress_bar.progress(
                    done / total_batches,
                    text=f"Ingesting… {min(done * BATCH_SIZE, NUM_ROWS)} / {NUM_ROWS}",
                )
        progress_bar.empty()
    except Exception as e:
        progress_bar.empty()
        st.error(f"Failed to load initial data: {str(e)}")
        raise


def _parse_vector(s: str) -> Optional[List[float]]:
    """Parse '[a,b,c]' or 'a,b,c' into list of 3 floats."""
    s = s.strip()
    if not s:
        return None
    if s.startswith("["):
        s = s[1:]
    if s.endswith("]"):
        s = s[:-1]
    parts = [x.strip() for x in s.split(",")]
    if len(parts) != VECTOR_DIM:
        return None
    try:
        return [float(x) for x in parts]
    except ValueError:
        return None


def perform_search(
    table: Table,
    query_vector: List[float],
    query_limit: int,
    distance_threshold: float,
) -> Tuple[List[Dict[str, Any]], Optional[str]]:
    """Run vector search by query vector and return (results, compiled_sql)."""
    try:
        search_query = (
            table.search(query_vector)
            .debug(True)
            .distance_threshold(distance_threshold)
            .limit(query_limit)
        )

        compiled_sql = search_query.compiled_vector_query_sql()
        results = search_query.to_list()
        return results, compiled_sql
    except Exception as e:
        st.error(f"Failed to perform vector search: {str(e)}")
        return [], None


def display_search_results(
    results: List[Dict[str, Any]], query_vector: List[float]
) -> None:
    if not results:
        st.info("No results found for your query.")
        return

    with st.expander(f"Query results ({len(results)} rows)", expanded=True):
        df = pd.DataFrame(results)
        display_order = ["id", "text", "text_vec", "_distance", "_score"]
        df = df[[c for c in display_order if c in df.columns]]

        column_config = {}
        if "text" in df.columns:
            column_config["text"] = st.column_config.Column(width=120)
        st.dataframe(df, hide_index=True, column_config=column_config or None)


def _format_sql(sql: str) -> str:
    """Format SQL for readable display."""
    return sqlparse.format(sql.strip(), reindent=True, keyword_case="upper")


def display_sql_and_plan(db: TiDBClient, compiled_sql: Optional[str]) -> None:
    if not compiled_sql or not compiled_sql.strip():
        return

    with st.expander("Executed SQL", expanded=False):
        st.code(_format_sql(compiled_sql), language="sql")

    with st.expander("TiDB execution plan (EXPLAIN ANALYZE)", expanded=True):
        st.caption(
            "Look at the **last row** of the execution plan: if the **access object** "
            "column shows an index object, the vector index is in use."
        )
        try:
            explain_sql = "EXPLAIN ANALYZE " + compiled_sql.strip().rstrip(";")
            result = db.query(explain_sql)
            plan_rows = result.to_list()
            if plan_rows:
                plan_df = pd.DataFrame(plan_rows)
                column_config = {
                    col: st.column_config.Column(
                        width=360 if col == "access object" else None
                    )
                    for col in plan_df.columns
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

    db = st.session_state.db
    if st.session_state.table is None:
        with st.spinner("Setting up vector table..."):
            st.session_state.table = setup_table(db)

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
            f"""#### Overview

This demo runs **vector search** on **{NUM_ROWS:,}** chunks with **3-dim random vectors** (no embedding API).
After each search you can see the **executed SQL** and **EXPLAIN ANALYZE** plan.
            """
        )

        st.markdown("#### Settings")
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
                    st.badge("Ready", icon=":material/check:", color="green")
                else:
                    st.badge(
                        "Not built yet", icon=":material/schedule:", color="orange"
                    )
            except Exception:
                st.badge("Unknown", color="gray")

        if table is not None:
            try:
                db = st.session_state.db
                replica = TiFlashReplica(table._sa_table, replica_count=1)
                progress = replica.get_replication_progress(db.db_engine)
                st.markdown("#### TiFlash replica")
                if progress["replica_count"] == 0:
                    st.caption("No TiFlash replica configured")
                else:
                    if progress["available"]:
                        st.badge(
                            f"Ready ({progress['progress']:.0%})",
                            icon=":material/check:",
                            color="green",
                        )
                    else:
                        st.badge(
                            f"Syncing ({progress['progress']:.0%})",
                            icon=":material/schedule:",
                            color="orange",
                        )
            except Exception:
                st.markdown("#### TiFlash replica")
                st.caption("Unknown")

    default_vec = "[0.1, 0.2, 0.3]"
    with st.form("search_form", clear_on_submit=False):
        col_label, col_input, col_btn = st.columns([2, 5, 2])
        with col_label:
            st.markdown(
                '<div style="display: flex; align-items: center; min-height: 38px; justify-content: flex-end;"><strong>Query vector:</strong></div>',
                unsafe_allow_html=True,
            )
        with col_input:
            st.text_input(
                "query_vector",
                value=st.session_state.get("query_vector_str", default_vec),
                placeholder="[x, y, z]",
                disabled=True,
                label_visibility="collapsed",
            )
        with col_btn:
            search_clicked = st.form_submit_button("Generate & Search")

    if search_clicked:
        new_vec = _random_vector(VECTOR_DIM)
        st.session_state["query_vector_str"] = (
            "[" + ",".join(str(round(x, 6)) for x in new_vec) + "]"
        )
        st.session_state.pending_search_vector = new_vec
        st.rerun()

    if st.session_state.pending_search_vector is None:
        st.markdown(
            '<p style="text-align: center;">Click <b>Generate & Search</b> to generate a random vector and run search.</p>',
            unsafe_allow_html=True,
        )
        return

    query_vector = st.session_state.pending_search_vector
    st.session_state.pending_search_vector = None

    with st.spinner("Searching for similar chunks..."):
        table = st.session_state.table
        db = st.session_state.db
        results, compiled_sql = perform_search(
            table, query_vector, query_limit, distance_threshold
        )

    display_search_results(results, query_vector)

    if compiled_sql:
        display_sql_and_plan(db, compiled_sql)


if __name__ == "__main__":
    main()
