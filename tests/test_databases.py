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
