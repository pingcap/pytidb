import os
import pytest
import uuid


def test_databases(shared_client):
    db_name = "test_db"
    if shared_client.has_database(db_name):
        shared_client.drop_database(db_name)

    # create database.
    shared_client.create_database(db_name)
    with pytest.raises(Exception):
        shared_client.create_database(db_name)
    shared_client.create_database(db_name, if_exists="skip")

    # list database names.
    db_names = shared_client.list_databases()
    assert db_name in db_names
    assert shared_client.has_database(db_name)

    # drop database.
    shared_client.drop_database(db_name)
    assert not shared_client.has_database(db_name)


@pytest.mark.skip(reason="slow test, need investigation")
def test_ensure_db(shared_client):
    db_name = "test_db"
    if shared_client.has_database(db_name):
        shared_client.drop_database(db_name)

    common_kwargs = {
        "host": os.getenv("TIDB_HOST", "localhost"),
        "port": int(os.getenv("TIDB_PORT", "4000")),
        "username": os.getenv("TIDB_USERNAME", "root"),
        "password": os.getenv("TIDB_PASSWORD", ""),
    }

    # Without ensure_db.
    with pytest.raises(Exception):
        shared_client.connect(**common_kwargs, database=db_name)

    # With ensure_db.
    temp_client = shared_client.connect(
        **common_kwargs,
        database=db_name,
        ensure_db=True,
    )
    assert temp_client is not None


def test_current_database(isolated_client):
    """Test that current_database() returns the correct database name."""
    # The fresh_client fixture creates a unique database name
    current_db = isolated_client.current_database()
    assert current_db is not None
    assert current_db.startswith("test_pytidb_")


def test_use_database_existing(isolated_client):
    """Test switching to an existing database."""
    # Get the initial database
    initial_db = isolated_client.current_database()

    # Create a new test database
    test_db = f"test_use_db_{uuid.uuid4().hex[:8]}"
    isolated_client.create_database(test_db)

    try:
        # Switch to the new database
        isolated_client.use_database(test_db)

        # Verify we're now in the new database
        assert isolated_client.current_database() == test_db

        # Switch back to the initial database
        isolated_client.use_database(initial_db)

        # Verify we're back in the initial database
        assert isolated_client.current_database() == initial_db

    finally:
        # Clean up
        isolated_client.drop_database(test_db)


def test_use_database_with_ensure_db(isolated_client):
    """Test switching to a non-existing database with ensure_db=True."""
    initial_db = isolated_client.current_database()
    test_db = f"test_ensure_db_{uuid.uuid4().hex[:8]}"

    # Ensure the database doesn't exist
    assert not isolated_client.has_database(test_db)

    try:
        # Switch to the new database with ensure_db=True
        isolated_client.use_database(test_db, ensure_db=True)

        # Verify the database was created and we're now using it
        assert isolated_client.has_database(test_db)
        assert isolated_client.current_database() == test_db

    finally:
        # Clean up
        isolated_client.use_database(initial_db)
        isolated_client.drop_database(test_db)


def test_use_database_nonexistent_without_ensure_db(isolated_client):
    """Test that switching to a non-existing database without ensure_db raises an error."""
    test_db = f"test_nonexistent_{uuid.uuid4().hex[:8]}"

    # Ensure the database doesn't exist
    assert not isolated_client.has_database(test_db)

    # Should raise ValueError when trying to switch to non-existing database
    with pytest.raises(ValueError, match=f"Database '{test_db}' does not exist"):
        isolated_client.use_database(test_db)


def test_use_database_persists_across_operations(isolated_client):
    """Test that the database context persists across various operations."""
    initial_db = isolated_client.current_database()
    test_db = f"test_persist_{uuid.uuid4().hex[:8]}"

    isolated_client.create_database(test_db)

    try:
        # Switch to the test database
        isolated_client.use_database(test_db)
        assert isolated_client.current_database() == test_db

        # Create a table in the test database
        isolated_client.execute(
            "CREATE TABLE test_table (id INT PRIMARY KEY, name VARCHAR(50))"
        )

        # Verify the table exists in the current database
        tables = isolated_client.list_tables()
        assert "test_table" in tables

        # Insert some data
        isolated_client.execute("INSERT INTO test_table (id, name) VALUES (1, 'test')")

        # Query the data
        result = isolated_client.query("SELECT * FROM test_table")
        rows = result.to_rows()
        assert len(rows) == 1
        assert rows[0][0] == 1
        assert rows[0][1] == "test"

        # Verify we're still in the correct database
        assert isolated_client.current_database() == test_db

    finally:
        # Clean up
        isolated_client.use_database(initial_db)
        isolated_client.drop_database(test_db)


def test_use_database_with_connection_url(shared_client):
    """Test use_database works with clients created using connection URLs."""
    initial_db = shared_client.current_database()
    test_db = f"test_url_{uuid.uuid4().hex[:8]}"

    shared_client.create_database(test_db)

    try:
        # Switch to the test database
        shared_client.use_database(test_db)
        assert shared_client.current_database() == test_db

        # Switch back
        shared_client.use_database(initial_db)
        assert shared_client.current_database() == initial_db

    finally:
        # Clean up
        shared_client.drop_database(test_db)


def test_multiple_database_switches(isolated_client):
    """Test multiple consecutive database switches."""
    initial_db = isolated_client.current_database()

    # Create multiple test databases
    test_dbs = [f"test_multi_{i}_{uuid.uuid4().hex[:8]}" for i in range(3)]

    for db in test_dbs:
        isolated_client.create_database(db)

    try:
        # Switch between databases multiple times
        for db in test_dbs:
            isolated_client.use_database(db)
            assert isolated_client.current_database() == db

            # Create a unique table in each database
            isolated_client.execute(
                f"CREATE TABLE table_{db[-8:]} (id INT PRIMARY KEY)"
            )
            tables = isolated_client.list_tables()
            assert f"table_{db[-8:]}" in tables

        # Switch back to each database and verify the table exists
        for db in test_dbs:
            isolated_client.use_database(db)
            tables = isolated_client.list_tables()
            assert f"table_{db[-8:]}" in tables

    finally:
        # Clean up
        isolated_client.use_database(initial_db)
        for db in test_dbs:
            isolated_client.drop_database(db)
