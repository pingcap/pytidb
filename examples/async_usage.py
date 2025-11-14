"""
Async PyTiDB Usage Examples

This script demonstrates how to use the new async API for PyTiDB.
The async API provides non-blocking database operations while maintaining
full compatibility with the existing synchronous API.
"""
import asyncio
import time
from typing import List, Dict, Any

from pytidb import AsyncTiDBClient, AsyncTable


async def basic_operations():
    """Demonstrate basic async CRUD operations."""
    print("=== Basic Async Operations ===")

    # Connect to database
    async with AsyncTiDBClient.connect(
        host="localhost",
        port=4000,
        username="root",
        password="",
        database="test_db"
    ) as client:
        print("✓ Connected to database")

        # Get table reference
        users_table = await client.get_table("users")
        print(f"✓ Got table: {users_table.name}")

        # Insert single record
        user_data = {
            "name": "Alice Johnson",
            "email": "alice@example.com",
            "age": 28,
            "city": "New York"
        }

        try:
            result = await users_table.insert(user_data)
            print(f"✓ Inserted user: {result}")
        except Exception as e:
            print(f"Insert failed (may already exist): {e}")

        # Query with filters
        query_result = await users_table.select(filters={"age": {"$gt": 25}})
        users = await query_result.to_list()
        print(f"✓ Found {len(users)} users over 25 years old")

        # Update records
        update_result = await users_table.update(
            {"status": "active"},
            filters={"age": {"$gte": 18}}
        )
        print(f"✓ Updated user status")

        # Count records
        count = await users_table.count()
        print(f"✓ Total users in database: {count}")


async def concurrent_operations():
    """Demonstrate concurrent async operations for performance."""
    print("\n=== Concurrent Operations ===")

    async with AsyncTiDBClient.connect(
        host="localhost",
        port=4000,
        database="test_db"
    ) as client:
        # Get multiple tables
        users_table = await client.get_table("users")
        products_table = await client.get_table("products")
        orders_table = await client.get_table("orders")

        # Run multiple operations concurrently
        start_time = time.time()

        tasks = [
            # Query different tables concurrently
            users_table.select(filters={"city": "New York"}),
            products_table.select(filters={"price": {"$lt": 100}}),
            orders_table.select(filters={"status": "pending"}),

            # Count operations
            users_table.count(filters={"age": {"$gt": 30}}),
            products_table.count(filters={"in_stock": True}),
        ]

        results = await asyncio.gather(*tasks)

        end_time = time.time()

        print(f"✓ Executed {len(tasks)} operations concurrently")
        print(f"✓ Total time: {end_time - start_time:.3f} seconds")

        # Process results
        ny_users, cheap_products, pending_orders, older_users, in_stock_products = results

        ny_users_list = await ny_users.to_list()
        cheap_products_list = await cheap_products.to_list()
        pending_orders_list = await pending_orders.to_list()

        print(f"✓ New York users: {len(ny_users_list)}")
        print(f"✓ Cheap products: {len(cheap_products_list)}")
        print(f"✓ Pending orders: {len(pending_orders_list)}")
        print(f"✓ Users over 30: {older_users}")
        print(f"✓ Products in stock: {in_stock_products}")


async def transaction_example():
    """Demonstrate transaction-like behavior with async operations."""
    print("\n=== Transaction Example ===")

    async with AsyncTiDBClient.connect(
        host="localhost",
        port=4000,
        database="test_db"
    ) as client:
        try:
            # Begin transaction-like sequence
            print("Starting transaction sequence...")

            # Execute multiple related operations
            await client.execute_sql("BEGIN")

            # Insert user
            await client.execute_sql(
                "INSERT INTO users (name, email, balance) VALUES (?, ?, ?)",
                params=["Bob Smith", "bob@example.com", 1000.00]
            )

            # Update balance
            await client.execute_sql(
                "UPDATE users SET balance = balance - ? WHERE email = ?",
                params=[100.00, "bob@example.com"]
            )

            # Record transaction
            await client.execute_sql(
                "INSERT INTO transactions (user_email, amount, type) VALUES (?, ?, ?)",
                params=["bob@example.com", -100.00, "debit"]
            )

            # Commit
            await client.execute_sql("COMMIT")
            print("✓ Transaction completed successfully")

        except Exception as e:
            # Rollback on error
            await client.execute_sql("ROLLBACK")
            print(f"✗ Transaction failed, rolled back: {e}")


async def batch_operations():
    """Demonstrate batch operations for efficiency."""
    print("\n=== Batch Operations ===")

    async with AsyncTiDBClient.connect(
        host="localhost",
        port=4000,
        database="test_db"
    ) as client:
        products_table = await client.get_table("products")

        # Prepare batch data
        products = [
            {"name": "Laptop", "price": 999.99, "category": "Electronics"},
            {"name": "Mouse", "price": 29.99, "category": "Electronics"},
            {"name": "Keyboard", "price": 79.99, "category": "Electronics"},
            {"name": "Monitor", "price": 299.99, "category": "Electronics"},
            {"name": "Headphones", "price": 149.99, "category": "Electronics"},
        ]

        # Insert products concurrently
        start_time = time.time()

        insert_tasks = [
            products_table.insert(product)
            for product in products
        ]

        results = await asyncio.gather(*insert_tasks)

        end_time = time.time()

        print(f"✓ Inserted {len(results)} products concurrently")
        print(f"✓ Batch insert time: {end_time - start_time:.3f} seconds")

        # Verify insertion
        count = await products_table.count()
        print(f"✓ Total products after batch insert: {count}")


async def raw_sql_queries():
    """Demonstrate raw SQL queries with async API."""
    print("\n=== Raw SQL Queries ===")

    async with AsyncTiDBClient.connect(
        host="localhost",
        port=4000,
        database="test_db"
    ) as client:
        # Complex query with joins
        sql = """
        SELECT u.name, u.email, COUNT(o.id) as order_count, SUM(o.total) as total_spent
        FROM users u
        LEFT JOIN orders o ON u.email = o.user_email
        GROUP BY u.name, u.email
        HAVING COUNT(o.id) > 0
        ORDER BY total_spent DESC
        LIMIT 10
        """

        result = await client.execute_sql(sql)
        top_customers = await result.to_list()

        print(f"✓ Top customers by spending:")
        for customer in top_customers:
            print(f"  {customer['name']}: ${customer['total_spent']:.2f} ({customer['order_count']} orders)")

        # Parameterized query
        email = "alice@example.com"
        user_result = await client.execute_sql(
            "SELECT * FROM users WHERE email = ?",
            params=[email]
        )

        user_data = await user_result.to_list()
        if user_data:
            print(f"✓ Found user: {user_data[0]['name']}")
        else:
            print(f"✓ User not found: {email}")


async def error_handling():
    """Demonstrate error handling in async operations."""
    print("\n=== Error Handling ===")

    try:
        async with AsyncTiDBClient.connect(
            host="invalid_host",
            port=4000,
            database="test_db",
            timeout=1
        ) as client:
            # This should fail
            pass
    except Exception as e:
        print(f"✓ Connection error handled: {type(e).__name__}")

    # Valid connection but invalid operations
    async with AsyncTiDBClient.connect(
        host="localhost",
        port=4000,
        database="test_db"
    ) as client:
        try:
            # Invalid SQL
            await client.execute_sql("INVALID SQL SYNTAX")
        except Exception as e:
            print(f"✓ SQL error handled: {type(e).__name__}")

        try:
            # Non-existent table
            table = await client.get_table("non_existent_table")
            await table.select()
        except Exception as e:
            print(f"✓ Table error handled: {type(e).__name__}")


async def performance_comparison():
    """Compare async vs sync performance (simulated)."""
    print("\n=== Performance Comparison ===")

    # Simulate multiple database operations
    async def simulate_db_operations():
        # Simulate 5 database operations
        for i in range(5):
            await asyncio.sleep(0.01)  # Simulate 10ms DB operation

    # Sequential execution
    start_time = time.time()
    for i in range(5):
        await simulate_db_operations()
    sequential_time = time.time() - start_time

    # Concurrent execution
    start_time = time.time()
    tasks = [simulate_db_operations() for _ in range(5)]
    await asyncio.gather(*tasks)
    concurrent_time = time.time() - start_time

    print(f"✓ Sequential execution time: {sequential_time:.3f}s")
    print(f"✓ Concurrent execution time: {concurrent_time:.3f}s")
    print(f"✓ Performance improvement: {(sequential_time/concurrent_time):.1f}x faster")


async def main():
    """Run all async examples."""
    print("Async PyTiDB Usage Examples")
    print("=" * 50)

    # Note: These examples use simulated data since we don't have a real database
    # In a real scenario, you would have actual database connections and data

    try:
        await basic_operations()
        await concurrent_operations()
        await transaction_example()
        await batch_operations()
        await raw_sql_queries()
        await error_handling()
        await performance_comparison()

        print("\n" + "=" * 50)
        print("All examples completed successfully! ✓")
        print("\nKey benefits of async PyTiDB:")
        print("• Non-blocking database operations")
        print("• Better resource utilization")
        print("• Improved application responsiveness")
        print("• Easier concurrent database operations")
        print("• Full compatibility with existing sync API")

    except Exception as e:
        print(f"\n✗ Error running examples: {e}")
        print("Note: These examples require a running TiDB instance.")
        print("The examples demonstrate the API usage with simulated data.")


if __name__ == "__main__":
    # Run the async examples
    asyncio.run(main())


# Additional standalone examples
async def quick_start():
    """Quick start guide for async PyTiDB."""
    # 1. Connect to database
    async with AsyncTiDBClient.connect(
        host="localhost",
        port=4000,
        database="myapp"
    ) as client:
        # 2. Get a table
        users_table = await client.get_table("users")

        # 3. Insert data
        await users_table.insert({
            "name": "John Doe",
            "email": "john@example.com",
            "age": 30
        })

        # 4. Query data
        result = await users_table.select(filters={"age": {"$gt": 25}})
        users = await result.to_list()

        print(f"Found {len(users)} users over 25 years old")


async def batch_insert_example():
    """Example of efficient batch inserts."""
    async with AsyncTiDBClient.connect(
        host="localhost",
        port=4000,
        database="myapp"
    ) as client:
        products_table = await client.get_table("products")

        # Prepare data
        products = [
            {"name": f"Product {i}", "price": i * 10.0}
            for i in range(100)
        ]

        # Insert concurrently
        tasks = [products_table.insert(product) for product in products]
        results = await asyncio.gather(*tasks)

        print(f"Inserted {len(results)} products concurrently")


# Example of using async context manager
async def context_manager_example():
    """Example using async context manager for automatic cleanup."""
    try:
        # Connection is automatically managed
        async with AsyncTiDBClient.connect(
            host="localhost",
            port=4000,
            database="myapp"
        ) as client:
            # Your database operations here
            table = await client.get_table("users")
            result = await table.select()
            users = await result.to_list()
            return users
    except Exception as e:
        print(f"Database operation failed: {e}")
        return []