"""Async TiDB Example

This example demonstrates how to use PyTiDB with asyncio for non-blocking
database operations. The async API provides the same functionality as the
sync API but with async/await syntax.
"""

import os
import asyncio
from dotenv import load_dotenv

# Import the async client
from pytidb.async_client import AsyncTiDBClient


async def create_users_table(client):
    """Create a sample users table."""
    await client.execute("""
        CREATE TABLE IF NOT EXISTS async_users (
            id INT PRIMARY KEY AUTO_INCREMENT,
            name VARCHAR(255),
            age INT,
            email VARCHAR(255)
        )
    """)
    print("✓ Created users table")


async def insert_sample_data(client):
    """Insert sample user data."""
    # Clear existing data
    await client.execute("DELETE FROM async_users")

    # Insert sample users
    users = [
        ("Alice", 28, "alice@example.com"),
        ("Bob", 34, "bob@example.com"),
        ("Charlie", 22, "charlie@example.com"),
        ("Diana", 45, "diana@example.com"),
        ("Eve", 19, "eve@example.com"),
    ]

    for name, age, email in users:
        await client.execute(
            "INSERT INTO async_users (name, age, email) VALUES (%s, %s, %s)",
            params=(name, age, email)
        )

    print(f"✓ Inserted {len(users)} sample users")


async def query_users_example(client):
    """Example of querying users."""
    print("\n--- Query Examples ---")

    # Get all users
    result = await client.query("SELECT * FROM async_users")
    users = await result.to_list()
    print(f"All users ({len(users)}):")
    for user in users:
        print(f"  - {user['name']}: {user['age']} years old")

    # Get users over 25
    result = await client.query(
        "SELECT * FROM async_users WHERE age > %s ORDER BY age",
        params=(25,)
    )
    adult_users = await result.to_list()
    print(f"\nUsers over 25 ({len(adult_users)}):")
    for user in adult_users:
        print(f"  - {user['name']}: {user['age']} years old")

    # Count users
    result = await client.query("SELECT COUNT(*) as count FROM async_users")
    count = await result.scalar()
    print(f"\nTotal users in database: {count}")


async def concurrent_queries_example(client):
    """Example of running multiple queries concurrently."""
    print("\n--- Concurrent Query Example ---")

    # Define multiple queries to run concurrently
    queries = [
        client.query("SELECT COUNT(*) FROM async_users WHERE age < 30"),
        client.query("SELECT COUNT(*) FROM async_users WHERE age >= 30 AND age < 40"),
        client.query("SELECT COUNT(*) FROM async_users WHERE age >= 40"),
    ]

    # Run all queries concurrently using asyncio.gather
    results = await asyncio.gather(*queries)

    # Get scalars concurrently (all async operations)
    young, middle, senior = await asyncio.gather(
        results[0].scalar(),
        results[1].scalar(),
        results[2].scalar(),
    )

    print(f"Age distribution:")
    print(f"  - Under 30: {young} users")
    print(f"  - 30-39: {middle} users")
    print(f"  - 40 and over: {senior} users")
    print(f"✓ All {len(queries)} queries executed concurrently")


async def list_databases_and_tables_example(client):
    """Example of listing databases and tables."""
    print("\n--- Database Info ---")

    # List databases
    databases = await client.list_databases()
    print(f"Databases: {databases[:5]}...")  # Show first 5

    # List tables
    tables = await client.list_tables()
    print(f"Tables in current database: {tables}")

    # Check if our table exists
    has_users = await client.has_table("async_users")
    print(f"Has async_users table: {has_users}")


async def transaction_example(client):
    """Example of transaction-like behavior using context manager."""
    print("\n--- Transaction Example ---")

    try:
        # Insert a new user
        result = await client.execute(
            "INSERT INTO async_users (name, age, email) VALUES (%s, %s, %s)",
            params=("Frank", 31, "frank@example.com")
        )

        if result.success:
            print(f"✓ Inserted 1 user. Rows affected: {result.rowcount}")
        else:
            print(f"✗ Insert failed: {result.message}")

    except Exception as e:
        print(f"✗ Transaction failed: {e}")


async def cleanup_example(client):
    """Clean up the example table."""
    print("\n--- Cleanup ---")
    await client.execute("DROP TABLE IF EXISTS async_users")
    print("✓ Dropped async_users table")


async def main():
    """Main example demonstrating async TiDB operations."""
    # Load environment variables
    load_dotenv()

    print("=" * 60)
    print("Async TiDB Example")
    print("=" * 60)

    # Note: In a real application, you'd use actual TiDB credentials.
    # For this example, we'll show the code pattern without connecting.
    print("\n⚠️  This example shows the async API usage pattern.")
    print("   To run with actual database, set TIDB_ environment variables.")

    if not os.getenv("TIDB_HOST"):
        print("\n" + "=" * 60)
        print("Example usage pattern (database connection skipped):")
        print("=" * 60)

        print("""
import asyncio
import os
from pytidb.async_client import AsyncTiDBClient

async def main():
    # Connect using async context manager
    async with AsyncTiDBClient.connect(
        host=os.getenv("TIDB_HOST"),
        port=int(os.getenv("TIDB_PORT")),
        username=os.getenv("TIDB_USERNAME"),
        password=os.getenv("TIDB_PASSWORD"),
        database=os.getenv("TIDB_DATABASE"),
        ensure_db=True,
    ) as client:
        # Your async operations here
        result = await client.query("SELECT * FROM users")
        users = await result.to_list()
        for user in users:
            print(user)

        # Run concurrent queries
        results = await asyncio.gather(
            client.query("SELECT COUNT(*) FROM users"),
            client.query("SELECT * FROM users LIMIT 10")
        )

asyncio.run(main())
        """)
        return 0

    print("\n✓ Environment variables found, connecting to TiDB...")

    # Connect to TiDB using async context manager
    try:
        async with AsyncTiDBClient.connect(
            host=os.getenv("TIDB_HOST"),
            port=int(os.getenv("TIDB_PORT", "4000")),
            username=os.getenv("TIDB_USERNAME", "root"),
            password=os.getenv("TIDB_PASSWORD", ""),
            database=os.getenv("TIDB_DATABASE", "test"),
            ensure_db=True,
        ) as client:
            print("✓ Connected to TiDB\n")

            # Run examples
            await create_users_table(client)
            await insert_sample_data(client)
            await query_users_example(client)
            await concurrent_queries_example(client)
            await list_databases_and_tables_example(client)
            await transaction_example(client)
            await cleanup_example(client)

        print("\n✓ Disconnected from TiDB")

    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback
        traceback.print_exc()
        return 1

    print("\n" + "=" * 60)
    print("✅ All async operations completed successfully!")
    print("=" * 60)
    return 0


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    exit(exit_code)
