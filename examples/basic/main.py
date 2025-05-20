import os
import dotenv
from pytidb import TiDBClient
from pytidb.schema import TableModel, Field, VectorField
from pytidb.datatype import JSON, Text


# Load environment variables
dotenv.load_dotenv()

# Connect to database
# Support .env configuration
# TIDB_HOST, TIDB_PORT, TIDB_USERNAME, TIDB_PASSWORD, TIDB_DATABASE
db = TiDBClient.connect(
    host=os.getenv("TIDB_HOST", "localhost"),
    port=int(os.getenv("TIDB_PORT", "4000")),
    username=os.getenv("TIDB_USERNAME", "root"),
    password=os.getenv("TIDB_PASSWORD", ""),
    database=os.getenv("TIDB_DATABASE", "test"),
)


# Define table schema
class Item(TableModel, table=True):
    __tablename__ = "items_in_basic_example"
    __table_args__ = {"extend_existing": True}

    id: int = Field(primary_key=True)
    content: str = Field(sa_type=Text)  # text
    embedding: list[float] = VectorField(dimensions=3)  # vector embedding
    meta: dict = Field(sa_type=JSON, default_factory=dict)  # metadata


# Create table
print("Creating table...")
item_table = db.create_table(schema=Item)
item_table.truncate()

# Create: Insert items
print("\n=== CREATE ===")
item_table.bulk_insert(
    [
        Item(
            id=1,
            content="TiDB is a distributed SQL database",
            embedding=[0.1, 0.2, 0.3],
            meta={"category": "database"},
        ),
        Item(
            id=2,
            content="GPT-4 is a large language model",
            embedding=[0.4, 0.5, 0.6],
            meta={"category": "llm"},
        ),
        Item(
            id=3,
            content="PyTiDB is a Python client for TiDB",
            embedding=[0.7, 0.8, 0.9],
            meta={"category": "database"},
        ),
    ]
)
print("Created 3 items")

# Read: Query all items
print("\n=== READ ===")
items = item_table.query(filters={"meta.category": "database"})
for item in items:
    print(f"ID: {item.id}, Content: {item.content}, Metadata: {item.meta}")

# Update: Modify an item
print("\n=== UPDATE ===")
item_id_to_update = 1
item_table.update(
    values={
        "content": "Updated item",
        "meta": {"category": "database"},
        "embedding": [0.1, 0.2, 0.3],
    },
    filters={"id": item_id_to_update},
)
print(f"Updated item with ID: {item_id_to_update}")

# Read again to verify update
updated_item = item_table.query(filters={"id": item_id_to_update})[0]
print(
    f"After update - ID: {updated_item.id}, Content: {updated_item.content}, Metadata: {updated_item.meta}"
)

# Delete: Remove an item
print("\n=== DELETE ===")
item_id_to_delete = 2
item_table.delete(filters={"id": item_id_to_delete})
print(f"Deleted item with ID: {item_id_to_delete}")

# Read again to verify deletion
print("\n=== FINAL STATE ===")
remaining_items = item_table.query()
if remaining_items:
    for item in remaining_items:
        print(f"ID: {item.id}, Content: {item.content}, Metadata: {item.meta}")
else:
    print("No items remaining.")

print("\nBasic CRUD operations completed!")
