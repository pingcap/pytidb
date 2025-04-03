def test_use_db(db):
    db_name = db.query("SELECT DATABASE()").scalar()
    assert db_name == "test"

    print(db.table_names())
    db.execute("USE pytidb_test")
    print(db.table_names())

    db_name = db.query("SELECT DATABASE()").scalar()
    assert db_name == "pytidb_test"
