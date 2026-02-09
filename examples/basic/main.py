import os
import dotenv

from pytidb import TiDBClient
from pytidb.schema import TableModel, Field, VectorField
from pytidb.datatype import JSON, TEXT


# Load environment variables
dotenv.load_dotenv()

# Connect to database with connection parameters
db = TiDBClient.connect(
    host=os.getenv("TIDB_HOST", "localhost"),
    port=int(os.getenv("TIDB_PORT", "4000")),
    username=os.getenv("TIDB_USERNAME", "root"),
    password=os.getenv("TIDB_PASSWORD", ""),
    database=os.getenv("TIDB_DATABASE", "basic_example"),
    ensure_db=True,
)

# Connect to database with connection string
# db = TiDBClient.connect(
#     database_url=os.getenv("TIDB_DATABASE_URL"),
# )

# Define table schema
print("=== CREATE TABLE ===")


class Item(TableModel):
    __tablename__ = "items_in_basic_example"
    id: int = Field(primary_key=True)
    content: str = Field(sa_type=TEXT)
    embedding: list[float] = VectorField(dimensions=3)
    meta: dict = Field(sa_type=JSON, default_factory=dict)


table = db.create_table(schema=Item, if_exists="overwrite")
print("Table created")

# Truncate table
print("\n=== TRUNCATE TABLE ===")
table.truncate()
print("Table truncated")

# Create: Insert items
print("\n=== CREATE ===")
table.insert(
    Item(
        id=1,
        content="TiDB is a distributed SQL database",
        embedding=[0.1, 0.2, 0.3],
        meta={"category": "database"},
    )
)
table.bulk_insert(
    [
        Item(
            id=2,
            content="GPT-4 is a large language model",
            embedding=[0.4, 0.5, 0.6],
            meta={"category": "llm"},
        ),
        Item(
            id=3,
            content="LlamaIndex is a Python library for building AI-powered applications",
            embedding=[0.7, 0.8, 0.9],
            meta={"category": "rag"},
        ),
    ]
)
print("Created 3 items")

# Read: Query all items
print("\n=== READ ===")
items = table.query(limit=10).to_pydantic()
for item in items:
    print(f"ID: {item.id}, Content: {item.content}, Metadata: {item.meta}")

# Update: Modify an item
print("\n=== UPDATE ===")
item_id_to_update = 1
table.update(
    values={
        "content": "TiDB Cloud Serverless is a fully-managed, auto-scaling cloud database service",
        "embedding": [0.1, 0.2, 0.4],
        "meta": {"category": "dbaas"},
    },
    filters={"id": item_id_to_update},
)
print(f"Updated item #{item_id_to_update}")

# Read again to verify update
updated_item = table.query(filters={"id": item_id_to_update}).to_pydantic()[0]
print(
    f"After update - ID: {updated_item.id}, Content: {updated_item.content}, Metadata: {updated_item.meta}"
)

# Delete: Remove an item
print("\n=== DELETE ===")
item_id_to_delete = 2
table.delete(filters={"id": item_id_to_delete})
print(f"Deleted item #{item_id_to_delete}")

# Read again to verify deletion
print("\n=== FINAL STATE ===")
remaining_items = table.query(limit=10).to_pydantic()
for item in remaining_items:
    print(f"ID: {item.id}, Content: {item.content}, Metadata: {item.meta}")

# Count rows
print("\n=== COUNT ROWS ===")
print(f"Number of rows: {table.rows()}")

# Drop table
print("\n=== DROP TABLE ===")
db.drop_table("items_in_basic_example")
print("Table dropped")

print("\nBasic CRUD operations completed!")
