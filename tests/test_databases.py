import os
import pytest


def test_databases(client):
    db_name = "test_db"
    if client.has_database(db_name):
        client.drop_database(db_name)

    # create database.
    client.create_database(db_name)
    with pytest.raises(Exception):
        client.create_database(db_name)
    client.create_database(db_name, skip_exists=True)

    # list database names.
    db_names = client.database_names()
    assert db_name in db_names
    assert client.has_database(db_name)

    # drop database.
    client.drop_database(db_name)
    assert not client.has_database(db_name)


@pytest.skip(reason="skipped until it can be finished fast", allow_module_level=True)
def test_ensure_db(client):
    db_name = "test_db"
    if client.has_database(db_name):
        client.drop_database(db_name)

    common_kwargs = {
        "host": os.getenv("TIDB_HOST", "localhost"),
        "port": int(os.getenv("TIDB_PORT", "4000")),
        "username": os.getenv("TIDB_USERNAME", "root"),
        "password": os.getenv("TIDB_PASSWORD", ""),
    }

    # Without ensure_db.
    with pytest.raises(Exception):
        client.connect(**common_kwargs, database=db_name)

    # With ensure_db.
    temp_client = client.connect(
        **common_kwargs,
        database=db_name,
        ensure_db=True,
    )
    assert temp_client is not None
