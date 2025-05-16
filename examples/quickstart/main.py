import os
from pytidb import TiDBClient
from pytidb.embeddings import EmbeddingFunction
from pytidb.schema import TableModel, Field
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# 1. Connect to TiDB (fill in your own parameters in .env)
db = TiDBClient.connect(
    host=os.getenv("TIDB_HOST"),
    port=int(os.getenv("TIDB_PORT", 4000)),
    username=os.getenv("TIDB_USERNAME"),
    password=os.getenv("TIDB_PASSWORD"),
    database=os.getenv("TIDB_DATABASE"),
)

# 2. Create embedding function (e.g., OpenAI, fill in your API key in .env)
text_embed = EmbeddingFunction(
    model_name="openai/text-embedding-3-small",
    api_key=os.getenv("OPENAI_API_KEY"),
)


# 3. Define table schema
class Chunk(TableModel, table=True):
    id: int = Field(primary_key=True)
    text: str = Field()
    text_vec: list[float] = text_embed.VectorField(source_field="text")
    user_id: int = Field()


# 4. Create table
table = db.create_table(schema=Chunk)

# 5. Insert data
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

# 6. Query data
print("Query result:", table.query().limit(3).all())

# 7. Semantic search
print(
    "Semantic search result:",
    table.search("A library for my artificial intelligence software").limit(3).all(),
)

# 8. Delete a row (delete row with id=1)
table.delete({"id": 1})

# 9. Drop table
db.drop_table("chunks")
