import os
import dotenv

import litellm
from litellm import completion
import streamlit as st

from pytidb import TiDBClient
from pytidb.schema import TableModel, Field
from pytidb.embeddings import EmbeddingFunction

dotenv.load_dotenv()
litellm.drop_params = True


# Define the embedding and LLM models
EMBEDDING_MODEL = "ollama/mxbai-embed-large"
LLM_MODEL = "ollama/gemma3:4b"
PROMPT_TEMPLATE = """Context information is below.
---------------------
{context}
---------------------
Given the information and not prior knowledge, answer the query
in a detailed and precise manner.

Query: {question}
Answer:"""


def stream_text_only(llm_response):
    for chunk in llm_response:
        yield chunk.choices[0].delta.content or ""


# Connect to TiDB
db = TiDBClient.connect(
    host=os.getenv("TIDB_HOST", "localhost"),
    port=int(os.getenv("TIDB_PORT", "4000")),
    username=os.getenv("TIDB_USERNAME", "root"),
    password=os.getenv("TIDB_PASSWORD", ""),
    database=os.getenv("TIDB_DATABASE", "test"),
)


# Define the Chunk table
text_embed = EmbeddingFunction(EMBEDDING_MODEL)


class Chunk(TableModel):
    __tablename__ = "chunks_for_ollama_rag"
    # Notice: Avoid table already defined error when streamlit rerun the script.
    __table_args__ = {"extend_existing": True}

    id: int = Field(primary_key=True)
    text: str = Field()
    text_vec: list[float] = text_embed.VectorField(
        source_field="text",
    )


table = db.create_table(schema=Chunk, if_exists="skip")


# Insert sample chunks
sample_chunks = [
    "Llamas are camelids known for their soft fur and use as pack animals.",
    "Python's GIL ensures only one thread executes bytecode at a time.",
    "TiDB is a distributed SQL database for HTAP and AI workloads.",
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
    chunks = [Chunk(text=text) for text in sample_chunks]
    table.bulk_insert(chunks)

# Initialize chat history
if "messages" not in st.session_state:
    st.session_state.messages = []

# Display chat messages from history on app rerun
if len(st.session_state.messages) > 0:
    for message in st.session_state.messages:
        st.chat_message(message["role"]).markdown(message["content"])
else:
    with st.chat_message("assistant"):
        st.markdown(
            """
        👋 Hello! I'm your AI assistant powered by TiDB.

        Try asking me:
        - What's TiDB?
        - How to deploy LLM locally?
        """
        )

# React to user input
final_response = ""
if user_question := st.chat_input("Say something ..."):
    st.chat_message("user").markdown(user_question)

    # Add user message to chat history
    messages = st.session_state.messages.copy()
    st.session_state.messages.append(
        {
            "role": "user",
            "content": user_question,
        }
    )

    final_response = ""
    with st.chat_message("assistant") as assistant_message:
        # Retrieve (R): search relevant chunks with user message.
        with st.status("Retrieving relevant documents...") as status:
            res = table.search(user_question).distance_threshold(0.5).limit(5)
            columns = ("id", "text", "_distance", "_score", "text_vec")
            st.dataframe(res.to_pandas(), column_order=columns, hide_index=True)
            status.update(label="Retrieved relevant documents", expanded=True)

        # Argument (A): Combine the retrieved chunks into the prompt.
        texts = [chunk.text for chunk in res.to_pydantic()]
        context = "\n\n".join(texts)
        prompt = PROMPT_TEMPLATE.format(question=user_question, context=context)

        # Generation (G): Call the LLM to generate answer based on the context.
        messages.append(
            {
                "role": "user",
                "content": prompt,
            }
        )
        llm_response = completion(
            api_base="http://localhost:11434",
            stream=True,
            model=LLM_MODEL,
            messages=messages,
        )
        final_response = st.write_stream(stream_text_only(llm_response))

    # Add assistant response to chat history
    st.session_state.messages.append({"role": "assistant", "content": final_response})
