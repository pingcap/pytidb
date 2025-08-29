import os
from pytidb import TiDBClient
from pytidb.embeddings import EmbeddingFunction
from pytidb.schema import TableModel, Field
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Connect to TiDB (fill in your own parameters in .env)
print("=== Connect to TiDB ===")
db = TiDBClient.connect(
    host=os.getenv("TIDB_HOST"),
    port=int(os.getenv("TIDB_PORT", 4000)),
    username=os.getenv("TIDB_USERNAME"),
    password=os.getenv("TIDB_PASSWORD"),
    database=os.getenv("TIDB_DATABASE", "quickstart_example"),
    ensure_db=True,
)
print("Connected to TiDB")


print("\n=== Create embedding function ===")
text_embed = EmbeddingFunction(
    model_name="openai/text-embedding-3-small",
    api_key=os.getenv("OPENAI_API_KEY"),
)
print("Embedding function created")


print("\n=== Create table ===")


class Chunk(TableModel, table=True):
    __tablename__ = "chunks"
    id: int = Field(primary_key=True)
    text: str = Field()
    text_vec: list[float] = text_embed.VectorField(source_field="text")
    user_id: int = Field()


table = db.create_table(schema=Chunk, if_exists="overwrite")
print("Table created")


print("\n=== Truncate table ===")
table.truncate()
print("Table truncated")


print("\n=== Insert data ===")
table.bulk_insert(
    [
        Chunk(
            text="PyTiDB is a Python library for developers to connect to TiDB.",
            user_id=2,
        ),
        Chunk(
            text="LlamaIndex is a framework for building AI applications.", user_id=2
        ),
        Chunk(
            text="OpenAI is a company and platform that provides AI models service and tools.",
            user_id=3,
        ),
    ]
)
print("Inserted 3 chunks")


print("\n=== Query data ===")
results = table.query(limit=3).to_pydantic()
for result in results:
    print(f"ID: {result.id}, Text: {result.text}, User ID: {result.user_id}")


print("\n=== Semantic search ===")
results = (
    table.search("A library for my artificial intelligence software").limit(3).to_list()
)
for result in results:
    print(
        f"ID: {result['id']}, Text: {result['text']}, User ID: {result['user_id']}, Distance: {result['_distance']}"
    )


print("\n=== Delete a row ===")
table.delete({"id": 1})
print("Deleted chunk #1")


print("\n=== Drop table ===")
db.drop_table("chunks")
print("Table dropped")
