import os

import dotenv
import litellm
import streamlit as st
import pandas as pd

from sqlalchemy import Text
from pytidb import TiDBClient
from pytidb.schema import TableModel, Field
from pytidb.embeddings import EmbeddingFunction
from pytidb.rerankers import Reranker


dotenv.load_dotenv()
litellm.drop_params = True

# Connect to TiDB

db = TiDBClient.connect(
    host=os.getenv("TIDB_HOST", "localhost"),
    port=int(os.getenv("TIDB_PORT", "4000")),
    username=os.getenv("TIDB_USERNAME", "root"),
    password=os.getenv("TIDB_PASSWORD", ""),
    database=os.getenv("TIDB_DATABASE", "test"),
    connect_args={"autocommit": True},
)
# database_url = "mysql://username:password@host:port/database"
# db = TiDBClient.connect(database_url)`


# Create document table

embed_fn = EmbeddingFunction(model_name="text-embedding-3-small")
reranker = Reranker(model_name="jina_ai/jina-reranker-v2-base-multilingual")


class Document(TableModel, table=True):
    __tablename__ = "documents_for_demo"
    __table_args__ = {"extend_existing": True}

    id: int = Field(primary_key=True)
    text: str = Field(sa_type=Text)
    text_vec: list[float] = embed_fn.VectorField(source_field="text")


table = db.create_table(schema=Document)

if not table.has_fts_index("text"):
    table.create_fts_index("text")


# Ingest sample documents

sample_documents = [
    "Ollama is an open-source platform that allows you to run large language models (LLMs) locally on your machine.",
    "LlamaIndex is the leading framework for building LLM-powered agents and AI applications over your data.",
    "LangChain is a framework for developing AI applications powered by large language models.",
    # For multi-language test.
    "TiDB is a database for AI applications with vector search, knowledge graphs, and operational data capabilities.",
    "TiDB是一个开源的NewSQL数据库，支持混合事务和分析处理（HTAP）工作负载。",
    "TiDBはオープンソースの分散型HTAPデータベースで、トランザクション処理と分析処理の両方をサポートしています。",
    "MySQL is a relational database management system.",
    "Redis is an in-memory data structure store.",
    "Docker containers package applications with their dependencies.",
    "HTTPS is a protocol for secure communication over the internet.",
    "SSH is a protocol for secure remote login from one computer to another.",
    "Blockchain is a distributed ledger technology that enables secure and transparent transactions.",
    "Autonomous vehicles are vehicles that can drive themselves without human intervention.",
    "Physical intelligence is the ability of machines to understand and reason about the physical world.",
    "Linux is a family of open-source Unix-like operating systems based on the Linux kernel.",
    "iOS is a smartphone operating system developed by Apple Inc.",
    "Android is an open-source mobile operating system developed by Google.",
    "Twitter is a social media platform that allows users to share and interact with messages called 'tweets'.",
    "Amazon is a platform for buying and selling products online.",
    "Azure is a cloud computing platform providing on-demand services to individuals and organizations.",
]


if table.rows() == 0:
    table.bulk_insert([Document(text=text) for text in sample_documents])


# Streamlit UI

st.title("🔍 Search Demo")

search_type = st.sidebar.selectbox(
    label="search type",
    options=["fulltext", "vector", "hybrid"],
    index=2,
)
distance_threshold = st.sidebar.slider(
    label="distance threshold",
    help="The vector distance between the query vector and the vectors should be within this threshold.",
    min_value=0.0,
    max_value=1.0,
    value=0.7,
    disabled=search_type == "fulltext",
)
limit = st.sidebar.slider(
    label="limit",
    help="The number of documents to return.",
    min_value=1,
    max_value=20,
    value=10,
)
sample_query_text = (
    "HTAP database"
    if search_type == "fulltext"
    else "A library to build artificial intelligence software"
)
query_text = st.text_input(
    label=f"Input your search query (e.g. '{sample_query_text}')",
)


if st.button("Search") and query_text:
    with st.spinner("Searching documents..."):
        df = (
            table.search(query_text, search_type=search_type)
            .distance_threshold(distance_threshold)
            .rerank(reranker, "text")
            .limit(limit)
            .to_pandas()
        )

        if df.size > 0:
            st.write("##### Search results:")
            columns_to_hide = ["text_vec"]
            if search_type != "vector":
                columns_to_hide.append("_match_score")
            df = df.drop(columns=columns_to_hide)
            st.dataframe(df, hide_index=True)
        else:
            st.info("No results found")
else:
    with st.spinner("Loading all documents..."):
        st.write("##### All documents:")
        docs = table.query()
        df = pd.DataFrame(
            [{"id": doc.id, "text": doc.text, "text_vec": doc.text_vec} for doc in docs]
        )
        st.dataframe(df, hide_index=True)
