import os
import dotenv
import json

from pytidb import TiDBClient
from pytidb.schema import FullTextField, TableModel, Field


# Load environment variables
dotenv.load_dotenv()

# Connect to TiDB database
print("=== CONNECT TO DATABASE ===")
db = TiDBClient.connect(
    host=os.getenv("TIDB_HOST", "localhost"),
    port=int(os.getenv("TIDB_PORT", "4000")),
    username=os.getenv("TIDB_USERNAME", "root"),
    password=os.getenv("TIDB_PASSWORD", ""),
    database=os.getenv("TIDB_DATABASE", "pytidb_fulltext_demo"),
    ensure_db=True,
)
print("Database connected\n")

# Create stock items table
print("=== CREATE TABLE ===")


class Item(TableModel):
    __tablename__ = "items"
    __table_args__ = {"extend_existing": True}

    id: int = Field(primary_key=True)
    title: str = FullTextField()
    language: str = Field(max_length=10)


table = db.open_table(Item)
if table is None:
    print("Loading sample items, it may take a while...")
    table = db.create_table(schema=Item, if_exists="overwrite")
    if table.rows() == 0:
        with open("sample_items.json", "r", encoding="utf-8") as f:
            sample_items = json.load(f)
        table.bulk_insert([Item(**item) for item in sample_items])
        print(f"Inserted {len(sample_items)} sample items")
print("Table ready\n")

# Search examples
print("=== SEARCH EXAMPLES ===")

# Example 1: Search in English
print("1. Search for 'Bluetooth headphones' in English:")
results = (
    table.search("Bluetooth headphones", search_type="fulltext")
    .filter(Item.language == "en")
    .limit(3)
    .to_list()
)
print(json.dumps(results, indent=2, ensure_ascii=False))
print()

# Example 2: Search in Chinese
print("2. Search for '蓝牙耳机' in Chinese:")
results = (
    table.search("蓝牙耳机", search_type="fulltext")
    .filter(Item.language == "zh")
    .limit(3)
    .to_list()
)
print(json.dumps(results, indent=2, ensure_ascii=False))
print()

print("=== SEARCH COMPLETED ===")
