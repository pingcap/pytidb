"""
Asyncio Support Example for PyTiDB

This example demonstrates how to use the async API with PyTiDB.
The async API provides non-blocking database operations using asyncio.

Requirements:
- Python 3.10+
- pytidb installed
"""

import asyncio
import os
from pytidb import AsyncTiDBClient, AsyncTable
from pytidb.schema import TableModel, Field


# Define a sample table schema
class User(TableModel):
    __tablename__ = "users"
    id: int = Field(primary_key=True)
    name: str = Field(max_length=100)
    email: str = Field(max_length=255)


async def basic_async_operations():
    """Demonstrate basic async operations."""

    # Connect to TiDB using async context manager
    # The connection will be automatically closed when exiting the context
    async with AsyncTiDBClient.connect(
        host=os.getenv("TIDB_HOST", "localhost"),
        port=int(os.getenv("TIDB_PORT", "4000")),
        username=os.getenv("TIDB_USERNAME", "root"),
        password=os.getenv("TIDB_PASSWORD", ""),
        database=os.getenv("TIDB_DATABASE", "test"),
        ensure_db=True,
    ) as client:
        print("✓ Connected to TiDB")

        # Create a table
        table = await client.create_table(schema=User, if_exists="skip")
        print(f"✓ Table '{table.table_name}' created or already exists")

        # Insert a single record
        user = await table.insert({"id": 1, "name": "Alice", "email": "alice@example.com"})
        print(f"✓ Inserted user: {user.name} ({user.email})")

        # Bulk insert multiple records
        users = await table.bulk_insert([
            {"id": 2, "name": "Bob", "email": "bob@example.com"},
            {"id": 3, "name": "Charlie", "email": "charlie@example.com"},
            {"id": 4, "name": "Diana", "email": "diana@example.com"},
        ])
        print(f"✓ Bulk inserted {len(users)} users")

        # Query all records
        result = await table.query()
        users_list = result.to_list()
        print(f"✓ Queried {len(users_list)} users from table")

        # Get a specific record by ID
        user = await table.get(1)
        print(f"✓ Retrieved user: {user.name}")

        # Update a record
        await table.update({"email": "alice.smith@example.com"}, {"id": 1})
        print("✓ Updated user email")

        # Count rows
        count = await table.rows()
        print(f"✓ Table has {count} rows")

        # Delete a record
        await table.delete({"id": 4})
        print("✓ Deleted user with id=4")

        # Truncate table (remove all records)
        await table.truncate()
        print("✓ Truncated table")


async def concurrent_operations():
    """Demonstrate concurrent async operations for better performance."""

    async with AsyncTiDBClient.connect(
        host=os.getenv("TIDB_HOST", "localhost"),
        port=int(os.getenv("TIDB_PORT", "4000")),
        username=os.getenv("TIDB_USERNAME", "root"),
        password=os.getenv("TIDB_PASSWORD", ""),
        database=os.getenv("TIDB_DATABASE", "test"),
        ensure_db=True,
    ) as client:

        table = await client.create_table(schema=User, if_exists="skip")

        print("\nRunning concurrent operations...")

        # Run multiple insert operations concurrently
        # This is much faster than sequential operations
        tasks = []
        for i in range(10, 20):
            task = table.insert({
                "id": i,
                "name": f"User{i}",
                "email": f"user{i}@example.com"
            })
            tasks.append(task)

        # Wait for all insert operations to complete
        results = await asyncio.gather(*tasks)
        print(f"✓ Concurrently inserted {len(results)} users")

        # Run multiple queries concurrently
        query_tasks = [table.get(i) for i in range(10, 15)]
        queried_users = await asyncio.gather(*query_tasks)
        print(f"✓ Concurrently queried {len(queried_users)} users")

        # Clean up
        await table.truncate()


async def raw_sql_operations():
    """Demonstrate raw SQL operations."""

    async with AsyncTiDBClient.connect(
        host=os.getenv("TIDB_HOST", "localhost"),
        port=int(os.getenv("TIDB_PORT", "4000")),
        username=os.getenv("TIDB_USERNAME", "root"),
        password=os.getenv("TIDB_PASSWORD", ""),
        database=os.getenv("TIDB_DATABASE", "test"),
        ensure_db=True,
    ) as client:

        print("\nRunning raw SQL operations...")

        # Execute DDL
        result = await client.execute("""
            CREATE TABLE IF NOT EXISTS products (
                id INT PRIMARY KEY,
                name VARCHAR(255),
                price DECIMAL(10, 2)
            )
        """)
        print(f"✓ Table created: {result.success}")

        # Insert with raw SQL
        result = await client.execute(
            "INSERT INTO products (id, name, price) VALUES (%(id)s, %(name)s, %(price)s)",
            {"id": 1, "name": "Laptop", "price": 999.99}
        )
        print(f"✓ Inserted product: {result.rowcount} rows affected")

        # Query with raw SQL
        query_result = await client.query("SELECT * FROM products WHERE price > %(min_price)s",
                                         {"min_price": 500.0})
        products = query_result.to_list()
        print(f"✓ Queried {len(products)} products")

        # Get scalar result
        count_result = await client.query("SELECT COUNT(*) FROM products")
        count = count_result.scalar()
        print(f"✓ Total products: {count}")

        # Clean up
        await client.execute("DROP TABLE IF EXISTS products")


async def database_management():
    """Demonstrate database management operations."""

    # Create client without connecting to a specific database
    client = await AsyncTiDBClient.connect(
        host=os.getenv("TIDB_HOST", "localhost"),
        port=int(os.getenv("TIDB_PORT", "4000")),
        username=os.getenv("TIDB_USERNAME", "root"),
        password=os.getenv("TIDB_PASSWORD", ""),
        database="mysql",  # Connect to system database
    )

    try:
        print("\nRunning database management operations...")

        # List databases
        databases = await client.list_databases()
        print(f"✓ Available databases: {databases[:5]}...")  # Show first 5

        # Check if database exists
        has_test_db = await client.has_database("test")
        print(f"✓ Has 'test' database: {has_test_db}")

        # Get current database
        current_db = await client.current_database()
        print(f"✓ Current database: {current_db}")

        # Create a new database
        if "async_example_db" not in databases:
            await client.create_database("async_example_db", if_exists="skip")
            print("✓ Created database 'async_example_db'")

        # Switch to the new database
        await client.use_database("async_example_db")
        print(f"✓ Switched to database: {await client.current_database()}")

        # Create a table in the new database
        table = await client.create_table(schema=User, if_exists="skip")
        print(f"✓ Created table '{table.table_name}' in new database")

        # Clean up
        await client.drop_database("async_example_db")
        print("✓ Dropped database 'async_example_db'")

    finally:
        await client.disconnect()


async def main():
    """Run all examples."""
    print("PyTiDB Asyncio Examples")
    print("=" * 50)

    try:
        # Run basic operations
        await basic_async_operations()

        # Run concurrent operations
        await concurrent_operations()

        # Run raw SQL operations
        await raw_sql_operations()

        # Run database management operations
        await database_management()

        print("\n" + "=" * 50)
        print("✓ All examples completed successfully!")

    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    # Run the async main function
    asyncio.run(main())
