import os
import dotenv
import streamlit as st
import litellm

from pytidb import TiDBClient
from pytidb.schema import TableModel, Field
from pytidb.embeddings import EmbeddingFunction
from pytidb.datatype import JSON


# Load environment variables.
dotenv.load_dotenv()
litellm.drop_params = True

# Connect to TiDB.
db = TiDBClient.connect(
    host=os.getenv("TIDB_HOST", "localhost"),
    port=int(os.getenv("TIDB_PORT", "4000")),
    username=os.getenv("TIDB_USERNAME", "root"),
    password=os.getenv("TIDB_PASSWORD", ""),
    database=os.getenv("TIDB_DATABASE", "pytidb_vector_search"),
    ensure_db=True,
)


# Define embedding function.
text_embed = EmbeddingFunction("ollama/mxbai-embed-large")


# Define table schema.
class Chunk(TableModel):
    __tablename__ = "chunks"
    __table_args__ = {"extend_existing": True}

    id: int = Field(primary_key=True)
    text: str = Field()
    text_vec: list[float] = text_embed.VectorField(
        source_field="text",
    )
    meta: dict = Field(sa_type=JSON)


table = db.create_table(schema=Chunk, if_exists="skip")

# Insert sample data.
sample_chunks = [
    {
        "text": "Llamas are camelids known for their soft fur and use as pack animals.",
        "meta": {"language": "english"},
    },
    {
        "text": "Python's GIL ensures only one thread executes bytecode at a time.",
        "meta": {"language": "english"},
    },
    {
        "text": "TiDB is a distributed SQL database with HTAP capabilities.",
        "meta": {"language": "english"},
    },
    {
        "text": "TiDB是一个开源的NewSQL数据库，支持混合事务和分析处理（HTAP）工作负载。",
        "meta": {"language": "chinese"},
    },
    {
        "text": "TiDBはオープンソースの分散型HTAPデータベースで、トランザクション処理と分析処理の両方をサポートしています。",
        "meta": {"language": "japanese"},
    },
    {
        "text": "Einstein's theory of relativity revolutionized modern physics.",
        "meta": {"language": "english"},
    },
    {
        "text": "The Great Wall of China stretches over 13,000 miles.",
        "meta": {"language": "english"},
    },
    {
        "text": "Ollama enables local deployment of large language models.",
        "meta": {"language": "english"},
    },
    {
        "text": "HTTP/3 uses QUIC protocol for improved web performance.",
        "meta": {"language": "english"},
    },
    {
        "text": "Kubernetes orchestrates containerized applications across clusters.",
        "meta": {"language": "english"},
    },
    {
        "text": "Blockchain technology enables decentralized transaction systems.",
        "meta": {"language": "english"},
    },
    {
        "text": "GPT-4 demonstrates remarkable few-shot learning capabilities.",
        "meta": {"language": "english"},
    },
    {
        "text": "Machine learning algorithms improve with more training data.",
        "meta": {"language": "english"},
    },
    {
        "text": "Quantum computing uses qubits instead of traditional bits.",
        "meta": {"language": "english"},
    },
    {
        "text": "Neural networks are inspired by the human brain's structure.",
        "meta": {"language": "english"},
    },
    {
        "text": "Docker containers package applications with their dependencies.",
        "meta": {"language": "english"},
    },
    {
        "text": "Cloud computing provides on-demand computing resources.",
        "meta": {"language": "english"},
    },
    {
        "text": "Artificial intelligence aims to mimic human cognitive functions.",
        "meta": {"language": "english"},
    },
    {
        "text": "Cybersecurity protects systems from digital attacks.",
        "meta": {"language": "english"},
    },
    {
        "text": "Big data analytics extracts insights from large datasets.",
        "meta": {"language": "english"},
    },
    {
        "text": "Internet of Things connects everyday objects to the internet.",
        "meta": {"language": "english"},
    },
    {
        "text": "Augmented reality overlays digital content on the real world.",
        "meta": {"language": "english"},
    },
]

if table.rows() == 0:
    with st.spinner("Loading sample chunks, it may take a while..."):
        table.bulk_insert([Chunk(**chunk) for chunk in sample_chunks])

# Initialize Web UI.
st.title("🔍 Vector Search Demo")

# Sidebar.
with st.sidebar:
    st.logo(
        "../assets/logo-full.svg", size="large", link="https://pingcap.github.io/ai/"
    )
    st.markdown(
        """#### Overview

**Vector search** offers a powerful solution for **semantic similarity** searches across
diverse data types, such as documents, images, audio, and video.
"""
    )
    st.markdown("#### Settings")
    query_limit = st.sidebar.slider("query limit", min_value=1, max_value=20, value=5)
    distance_threshold = st.sidebar.slider(
        "distance threshold", min_value=0.0, max_value=1.0, value=0.5
    )
    st.markdown("##### Metadata Filter")
    language = st.selectbox(
        "Language", ["all", "english", "chinese", "japanese"], index=0
    )

# Search form.
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
    with st.spinner("Searching for similar chunks..."):
        search_query = table.search(query_text)
        if language != "all":
            search_query = search_query.filter({"meta.language": language})
        df = (
            search_query.distance_threshold(distance_threshold)
            .debug(True)
            .limit(query_limit)
            .to_pandas()
        )
        if len(df) > 0:
            st.markdown(
                f'Found <b>{len(df)}</b> results for <b>"{query_text}"</b>',
                unsafe_allow_html=True,
            )
            df = df.drop(columns=["text_vec"])
            st.dataframe(df, hide_index=True)
        else:
            st.empty()
