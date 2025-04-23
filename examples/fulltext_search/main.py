import os

import dotenv
import litellm
import streamlit as st
import pandas as pd
from sqlalchemy import Text

from pytidb import TiDBClient
from pytidb.schema import TableModel, Field

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
# db = TiDBClient.connect(database_url)`


# Create document table


class Document(TableModel, table=True):
    __tablename__ = "documents_for_fts"
    __table_args__ = {"extend_existing": True}

    id: int = Field(primary_key=True)
    text: str = Field(sa_type=Text)


table = db.create_table(schema=Document)

if not table.has_fts_index("text"):
    table.create_fts_index("text")

# Ingest sample documents

sample_documents = [
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

if table.rows() == 0:
    table.bulk_insert([Document(text=text) for text in sample_documents])


# Streamlit UI
st.title("🔍 Fulltext Search Demo")
query_limit = st.sidebar.slider("query limit", min_value=1, max_value=20, value=10)

# Add sample code display
with st.expander("Show Sample Code"):
    st.code(
        """from pytidb import TiDBClient
from pytidb.schema import TableModel, Field
from sqlalchemy import Text

db = TiDBClient.connect(
    host="localhost",
    port=4000,
    username="root",
    password="",
    database="test",
)

# Define document table
class Document(TableModel, table=True):
    __tablename__ = "documents_for_fts"
    id: int = Field(primary_key=True)
    text: str = Field(sa_type=Text)

# Create table and FTS index
table = db.create_table(schema=Document)
table.create_fts_index("text")

# Search documents
results = (
    table
    .search("your query", search_type="fulltext")
    .limit(10)
    .to_pandas()
)
""",
        language="python",
    )

st.write("Input your search query (e.g. 'HTAP database')")


query_text = st.text_input("", "")

if st.button("Search") and query_text:
    with st.spinner("Searching documents containing the keyword..."):
        df = (
            table.search(query_text, search_type="fulltext")
            .limit(query_limit)
            .to_pandas()
        )

        if df.size > 0:
            st.write("### Search results:")
            df = df.drop(columns=["_score"])
            st.dataframe(df)
        else:
            st.info("No results found")
else:
    with st.spinner("Loading all documents..."):
        docs = table.query()
        df = pd.DataFrame([{"id": doc.id, "text": doc.text} for doc in docs])
        st.write("### All documents:")
        st.dataframe(df)
