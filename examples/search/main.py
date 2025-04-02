import os

import dotenv
import litellm
import streamlit as st
from typing import Optional, Any
from pytidb import TiDBClient
from pytidb.schema import TableModel, Field
from pytidb.embeddings import EmbeddingFunction


dotenv.load_dotenv()
litellm.drop_params = True

db = TiDBClient.connect(
    host=os.getenv("TIDB_HOST", "localhost"),
    port=int(os.getenv("TIDB_PORT", "4000")),
    username=os.getenv("TIDB_USERNAME", "root"),
    password=os.getenv("TIDB_PASSWORD", ""),
    database=os.getenv("TIDB_DATABASE", "test"),
)
# database_url = "mysql://username:password@host:port/database"
# db = TiDBClient.connect(database_url)

text_embed = EmbeddingFunction("ollama/mxbai-embed-large")


class Chunk(TableModel, table=True):
    __tablename__ = "chunks"
    __table_args__ = {"extend_existing": True}

    id: int = Field(primary_key=True)
    text: str = Field()
    text_vec: Optional[Any] = text_embed.VectorField(
        source_field="text",
    )


sample_chunks = [
    "Llamas are camelids known for their soft fur and use as pack animals.",
    "Python's GIL ensures only one thread executes bytecode at a time.",
    "TiDB is a distributed SQL database with HTAP capabilities.",
    "Einstein's theory of relativity revolutionized modern physics.",
    "The Great Wall of China stretches over 13,000 miles.",
    "Ollama enables local deployment of large language models.",
    "HTTP/3 uses QUIC protocol for improved web performance.",
    "Kubernetes orchestrates containerized applications across clusters.",
    "Blockchain technology enables decentralized transaction systems.",
    "GPT-4 demonstrates remarkable few-shot learning capabilities.",
    "Machine learning algorithms improve with more training data.",
    "Quantum computing uses qubits instead of traditional bits.",
    "Neural networks are inspired by the human brain's structure.",
    "Docker containers package applications with their dependencies.",
    "Cloud computing provides on-demand computing resources.",
    "Artificial intelligence aims to mimic human cognitive functions.",
    "Cybersecurity protects systems from digital attacks.",
    "Big data analytics extracts insights from large datasets.",
    "Internet of Things connects everyday objects to the internet.",
    "Augmented reality overlays digital content on the real world.",
]

table = db.create_table(schema=Chunk)
if table.rows() == 0:
    chunks = [Chunk(text=text) for text in sample_chunks]
    table.bulk_insert(chunks)

st.title("🔍 Search Demo")
st.write("Input search query, find similar chunks")
query_limit = st.sidebar.slider("query limit", min_value=1, max_value=20, value=10)
query = st.text_input("Search:", "")

if st.button("Search") and query:
    with st.spinner("Searching for similar chunks..."):
        res = table.search(query).limit(query_limit)
        if res:
            st.write("### Search results:")
            st.dataframe(res.to_pandas())
        else:
            st.info("No relevant results found")
