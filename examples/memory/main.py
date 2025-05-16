import os
import dotenv
from openai import OpenAI
from pytidb import TiDBClient
import datetime
from typing import List, Dict, Any
from pytidb.embeddings import EmbeddingFunction
from pytidb.schema import TableModel, Field, Column
from pytidb.datatype import Text

dotenv.load_dotenv()

# Initialize clients
openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
tidb_client = TiDBClient.connect(
    host=os.getenv("TIDB_HOST"),
    port=int(os.getenv("TIDB_PORT", 4000)),
    username=os.getenv("TIDB_USERNAME"),
    password=os.getenv("TIDB_PASSWORD"),
    database=os.getenv("TIDB_DATABASE"),
)
embedding_fn = EmbeddingFunction(
    model_name="text-embedding-3-small", api_key=os.getenv("OPENAI_API_KEY")
)


class MemoryRecord(TableModel, table=True):
    __tablename__ = "memories"
    id: int = Field(default=None, primary_key=True)
    user_id: str
    memory: str = Field(sa_column=Column(Text))
    embedding: List[float] = embedding_fn.VectorField(source_field="memory")
    created_at: datetime.datetime = Field(
        default_factory=lambda: datetime.datetime.now(datetime.UTC)
    )


class Memory:
    def __init__(self):
        self.table = tidb_client.create_table(schema=MemoryRecord)

    def add(self, messages: List[Dict[str, Any]], user_id: str = "default_user"):
        prompt = """Extract the key facts from the following conversation. Only return the facts as a single string, do not include any explanation or formatting.\n\n"""
        for m in messages:
            prompt += f"{m['role']}: {m['content']}\n"
        response = openai_client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": prompt},
            ],
        )
        facts = response.choices[0].message.content.strip()

        record = MemoryRecord(user_id=user_id, memory=facts)
        self.table.insert(record)

    def search(
        self, query: str, user_id: str = "default_user", limit: int = 3
    ) -> Dict[str, Any]:
        results = (
            self.table.search(query=query, search_type="vector").limit(limit).to_list()
        )
        return {"results": results}


memory = Memory()


def chat_with_memories(message: str, user_id: str = "default_user") -> str:
    # Retrieve relevant memories
    relevant_memories = memory.search(query=message, user_id=user_id, limit=3)
    memories_str = "\n".join(
        f"- {entry['memory']}" for entry in relevant_memories["results"]
    )

    # Generate Assistant response
    system_prompt = f"You are a helpful AI. Answer the question based on query and memories.\nUser Memories:\n{memories_str}"
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": message},
    ]
    response = openai_client.chat.completions.create(
        model="gpt-4o-mini", messages=messages
    )
    assistant_response = response.choices[0].message.content

    # Create new memories from the conversation
    messages.append({"role": "assistant", "content": assistant_response})
    memory.add(messages, user_id=user_id)

    return assistant_response


def main():
    print("Chat with AI (type 'exit' to quit)")
    while True:
        user_input = input("You: ").strip()
        if user_input.lower() == "exit":
            print("Goodbye!")
            break
        print(f"AI: {chat_with_memories(user_input)}")


if __name__ == "__main__":
    main()
