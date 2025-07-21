import os
import pytest
import uuid


def test_manage_database(shared_client):
    """Test database management."""

    current_db = shared_client.current_database()
    assert current_db is not None
    assert current_db.startswith("test_pytidb_")

    # Create a new test database.
    test_db = f"test_create_db_{uuid.uuid4().hex[:8]}"
    assert not shared_client.has_database(test_db)

    # create database.
    shared_client.create_database(test_db)
    with pytest.raises(Exception):
        shared_client.create_database(test_db)  # Already exists, raise error.
    shared_client.create_database(test_db, if_exists="skip")  # Skip, no error.
    assert shared_client.has_database(test_db)

    # list database names.
    db_names = shared_client.list_databases()
    assert test_db in db_names
    assert shared_client.has_database(test_db)

    # drop database.
    shared_client.drop_database(test_db)
    assert not shared_client.has_database(test_db)


def test_create_database_with_ensure(shared_client):
    test_db = f"test_create_with_ensure_{uuid.uuid4().hex[:8]}"
    assert not shared_client.has_database(test_db)

    common_kwargs = {
        "host": os.getenv("TIDB_HOST", "localhost"),
        "port": int(os.getenv("TIDB_PORT", "4000")),
        "username": os.getenv("TIDB_USERNAME", "root"),
        "password": os.getenv("TIDB_PASSWORD", ""),
    }

    # Without ensure_db, raise an error because the database does not exist.
    with pytest.raises(Exception):
        shared_client.connect(**common_kwargs, database=test_db)

    # With ensure_db, create the database if it does not exist.
    temp_client = shared_client.connect(
        **common_kwargs,
        database=test_db,
        ensure_db=True,
    )
    assert temp_client is not None


def test_use_database(isolated_client):
    """Test switching to an existing database."""
    # Get the initial database
    initial_db = isolated_client.current_database()

    # Create a new test database
    test_db = f"test_use_db_{uuid.uuid4().hex[:8]}"
    isolated_client.create_database(test_db)

    try:
        # Switch to the new database
        isolated_client.use_database(test_db)
        assert isolated_client.current_database() == test_db

        # Switch back to the initial database
        isolated_client.use_database(initial_db)
        assert isolated_client.current_database() == initial_db
    finally:
        # Clean up the test database.
        isolated_client.drop_database(test_db)


def test_use_database_with_ensure(isolated_client):
    initial_db = isolated_client.current_database()
    test_db = f"test_use_db_with_ensure_{uuid.uuid4().hex[:8]}"

    # Without ensure_db, raise an error because the database does not exist.
    assert not isolated_client.has_database(test_db)
    with pytest.raises(ValueError, match=f"Database '{test_db}' does not exist"):
        isolated_client.use_database(test_db)

    try:
        # With ensure_db=True, create the database if it does not exist.
        isolated_client.use_database(test_db, ensure_db=True)
        assert isolated_client.has_database(test_db)
        assert isolated_client.current_database() == test_db
    finally:
        # Clean up the test database.
        isolated_client.use_database(initial_db)
        isolated_client.drop_database(test_db)
