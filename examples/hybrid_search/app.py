import os

import dotenv
import streamlit as st

from pytidb import TiDBClient
from pytidb.schema import FullTextField, TableModel, Field
from pytidb.embeddings import EmbeddingFunction
from pytidb.rerankers import Reranker

# Load environment variables.
dotenv.load_dotenv()


# Connect to TiDB
db = TiDBClient.connect(
    host=os.getenv("TIDB_HOST", "localhost"),
    port=int(os.getenv("TIDB_PORT", "4000")),
    username=os.getenv("TIDB_USERNAME", "root"),
    password=os.getenv("TIDB_PASSWORD", ""),
    database=os.getenv("TIDB_DATABASE", "pytidb_hybrid_demo"),
    ensure_db=True,
)


# Create embedding function.
embed_fn = EmbeddingFunction(
    model_name="text-embedding-3-small", api_key=os.getenv("OPENAI_API_KEY")
)


# Define reranker.
if os.getenv("JINA_AI_API_KEY") is not None:
    # Go to Jina AI Website (https://jina.ai/embeddings) to create a new API key.
    reranker = Reranker(
        model_name="jina_ai/jina-reranker-v2-base-multilingual",
        api_key=os.getenv("JINA_AI_API_KEY"),
    )
else:
    reranker = None


# Define table schema.
class Document(TableModel):
    __tablename__ = "documents"
    __table_args__ = {"extend_existing": True}

    id: int = Field(primary_key=True)
    text: str = FullTextField()
    text_vec: list[float] = embed_fn.VectorField(source_field="text")


# Sample documents
sample_documents = [
    "Ollama is an open-source platform that allows you to run large language models (LLMs) locally on your machine.",
    "In the near future, a lonely writer develops an unlikely relationship with an operating system designed to meet his every need.",
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
    "Linux is a family of open-source Unix-like operating systems based on the Linux kernel.",
    "iOS is a smartphone operating system developed by Apple Inc.",
    "Android is an open-source mobile operating system developed by Google.",
    "Twitter is a social media platform that allows users to share and interact with messages called 'tweets'.",
    "Amazon is a platform for buying and selling products online.",
    "Azure is a cloud computing platform providing on-demand services to individuals and organizations.",
]

table = db.open_table(Document)
if table is None:
    with st.spinner("Loading sample documents, it may take a while..."):
        table = db.create_table(schema=Document, mode="exist_ok")
        if table.rows() == 0:
            table.bulk_insert([Document(text=text) for text in sample_documents])

# Streamlit UI

# Sidebar.
with st.sidebar:
    st.logo(
        "../assets/logo-full.svg", size="large", link="https://pingcap.github.io/ai/"
    )
    st.markdown("""#### Overview

**Hybrid search** fuses **exact matching** from full-text search with **semantic understanding** 
from vector search, delivering more relevant and reliable results.

    """)
    st.markdown("#### Settings")
    search_type = st.selectbox(
        label="Search type",
        options=["fulltext", "vector", "hybrid"],
        index=2,
    )
    distance_threshold = st.slider(
        label="Distance threshold",
        help="The vector distance between the query vector and the vectors should be within this threshold.",
        min_value=0.0,
        max_value=1.0,
        value=0.7,
        disabled=search_type == "fulltext",
    )
    fusion_method_options = {
        "rrf": "Reciprocal Rank Fusion (RRF)",
        "weighted": "Weighted Score Fusion",
    }
    fusion_method = st.selectbox(
        label="Fusion method",
        options=fusion_method_options.keys(),
        format_func=lambda x: fusion_method_options[x],
        help="The method specifies how to fuse the scores from the vector search and the full-text search.",
        index=0,
    )
    limit = st.slider(
        label="Limit",
        help="The number of documents to return.",
        min_value=1,
        max_value=20,
        value=10,
    )


# Main content.
st.markdown(
    '<h3 style="text-align: center; padding-top: 40px;">Hybrid Search Demo</h3>',
    unsafe_allow_html=True,
)

with st.form("search_form"):
    col1, col2 = st.columns([6, 1])
    with col1:
        query_text = st.text_input(
            "Keywords:",
            placeholder="Enter your search query",
            label_visibility="collapsed",
        )
        st.markdown(
            'Try searching for: <b>"HTAP database"</b>',
            unsafe_allow_html=True,
        )
    with col2:
        submitted = st.form_submit_button("Search")

# Search results.
if submitted:
    with st.spinner("Searching documents containing the keyword..."):
        query = (
            table.search(query_text, search_type=search_type)
            .distance_threshold(distance_threshold)
            .fusion(method=fusion_method)
        )

        if reranker is not None:
            query = query.rerank(reranker, "text")

        df = query.limit(limit).to_pandas()

        if len(df) > 0:
            st.markdown(
                f'Found <b>{len(df)}</b> results for <b>"{query_text}"</b>',
                unsafe_allow_html=True,
            )
            df = df.drop(columns=["text_vec"])
            st.dataframe(df, hide_index=True)
        else:
            st.empty()
