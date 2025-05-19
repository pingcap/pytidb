import os
import dotenv
from typing import Optional
from pytidb import TiDBClient
from pytidb.schema import TableModel, Field

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
    __tablename__ = "items"
    __table_args__ = {"extend_existing": True}

    id: int = Field(primary_key=True)
    name: str = Field()
    description: Optional[str] = Field(default=None)


# Create table
print("Creating table...")
item_table = db.create_table(schema=Item)
item_table.truncate()

# Create: Insert items
print("\n=== CREATE ===")
item_table.bulk_insert(
    [
        Item(name="First item", description="This is item #1"),
        Item(name="Second item", description="This is item #2"),
        Item(name="Third item", description="This is item #3"),
    ]
)
print("Created 3 items")

# Read: Query all items
print("\n=== READ ===")
items = item_table.query()
for item in items:
    print(f"ID: {item.id}, Name: {item.name}, Description: {item.description}")

# Update: Modify an item
print("\n=== UPDATE ===")
item_id_to_update = 1
item_table.update(
    values={"name": "Updated item", "description": "This item was updated"},
    filters={"id": item_id_to_update},
)
print(f"Updated item with ID: {item_id_to_update}")

# Read again to verify update
updated_item = item_table.query({"id": item_id_to_update})[0]
print(
    f"After update - ID: {updated_item.id}, Name: {updated_item.name}, Description: {updated_item.description}"
)

# Delete: Remove an item
print("\n=== DELETE ===")
item_id_to_delete = 2
item_table.delete({"id": item_id_to_delete})
print(f"Deleted item with ID: {item_id_to_delete}")

# Read again to verify deletion
print("\n=== FINAL STATE ===")
remaining_items = item_table.query()
if remaining_items:
    for item in remaining_items:
        print(f"ID: {item.id}, Name: {item.name}, Description: {item.description}")
else:
    print("No items remaining.")

print("\nBasic CRUD operations completed!")
