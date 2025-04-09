import os
import dotenv

import litellm
from litellm import completion
import streamlit as st

from typing import Optional, Any
from pytidb import TiDBClient
from pytidb.schema import TableModel, Field
from pytidb.embeddings import EmbeddingFunction

dotenv.load_dotenv()
litellm.drop_params = True

# RAG prompt template
RAG_PROMPT_TEMPLATE = """Answer the question based on the following reference information.

Reference Information:
{context}

Question: {question}

Please answer:"""

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
llm_model = "ollama/llama3.2:3b"


# Define the Chunk table
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
# insert sample chunks
if table.rows() == 0:
    chunks = [Chunk(text=text) for text in sample_chunks]
    table.bulk_insert(chunks)


st.title("🔍 RAG Demo")
st.write(
    "Enter your question, and the system will retrieve relevant knowledge and generate an answer"
)
mode = st.radio("Select Mode:", ["Retrieval Only", "RAG Q&A"])

query_limit = st.sidebar.slider("Retrieval Limit", min_value=1, max_value=20, value=5)
query = st.text_input("Enter your question:", "")

if st.button("Send") and query:
    with st.spinner("Processing..."):
        # Retrieve relevant chunks
        res = table.search(query).limit(query_limit)

        if res:
            if mode == "Retrieval Only":
                st.write("### Retrieval Results:")
                st.dataframe(res.to_pandas())
            else:
                text = [chunk.text for chunk in res.to_rows()]

                # Build RAG prompt
                context = "\n".join(text)
                prompt = RAG_PROMPT_TEMPLATE.format(context=context, question=query)

                # Call LLM to generate answer
                response = completion(
                    model=llm_model,
                    messages=[{"content": prompt, "role": "user"}],
                    api_base="http://localhost:11434",
                )

                st.markdown(f"### 🤖 {llm_model}")
                st.markdown(
                    """
                <style>
                .llm-response {
                    background: rgba(255, 255, 255, 0.05);
                    padding: 25px;
                    border-radius: 15px;
                    box-shadow: 0 4px 6px rgba(0, 0, 0, 0.2);
                    border: 1px solid rgba(255, 255, 255, 0.1);
                    margin: 15px 0;
                    font-size: 1.1em;
                    line-height: 1.6;
                    color: #e1e4e8;
                }
                .llm-response:hover {
                    background: rgba(255, 255, 255, 0.08);
                    box-shadow: 0 6px 12px rgba(0, 0, 0, 0.3);
                    transition: all 0.3s ease;
                }
                </style>
                """,
                    unsafe_allow_html=True,
                )

                # show the response
                st.markdown(
                    f'<div class="llm-response">{response.choices[0].message.content}</div>',
                    unsafe_allow_html=True,
                )

                with st.expander("📚 Retrieved Knowledge", expanded=False):
                    st.dataframe(res.to_pandas())
        else:
            st.info("No relevant information found")
