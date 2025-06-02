def test_databases(client):
    db_name = "test_db"
    if client.has_database(db_name):
        client.drop_database(db_name)

    client.create_database(db_name)
    db_names = client.database_names()
    assert db_name in db_names
    assert client.has_database(db_name)

    client.drop_database(db_name)
    assert not client.has_database(db_name)
