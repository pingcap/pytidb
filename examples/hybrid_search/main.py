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
    "TiDB is a database for AI applications with vector search, knowledge graphs, and operational data capabilities.",
    "Ollama is an open-source platform that allows you to run large language models (LLMs) locally on your machine.",
    "GPT-4 is a multimodal large language model created by OpenAI, the fourth in its GPT series.",
    "LlamaIndex is the leading framework for building LLM-powered agents over your data.",
    "LangChain is a framework for developing applications powered by large language models.",
    "OpenAI is an AI research organization founded in 2015 and based in San Francisco.",
    "TiDB是一个开源的NewSQL数据库，支持混合事务和分析处理（HTAP）工作负载。",
    "TiDBはオープンソースの分散型HTAPデータベースで、トランザクション処理と分析処理の両方をサポートしています。",
    "AWS is a cloud computing platform providing on-demand services to individuals and organizations.",
    "Langfuse is an open-source LLM engineering platform that helps teams debug and analyze LLM applications.",
    "Machine learning algorithms improve with more training data.",
    "Neural networks are inspired by the human brain's structure.",
    "Docker containers package applications with their dependencies.",
    "Artificial intelligence aims to mimic human cognitive functions.",
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
    else "A library for my artificial intelligence software"
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
            df = df.drop(columns=["text_vec", "_match_score"])
            st.dataframe(
                df, hide_index=True, column_order=["id", "text", "_distance", "_score"]
            )
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
