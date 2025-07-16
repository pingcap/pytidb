from pytidb.utils import build_tidb_dsn


def test_build_tidb_dsn():
    # For TiDB Serverless
    dsn = build_tidb_dsn(
        host="gateway01.us-west-2.prod.aws.tidbcloud.com",
        username="xxxxxxxx.root",
        password="$password$",
    )
    assert (
        str(dsn)
        == "mysql+pymysql://xxxxxxxx.root:%24password%24@gateway01.us-west-2.prod.aws.tidbcloud.com:4000/test?ssl_verify_cert=true&ssl_verify_identity=true"
    )

    # For TiDB Cluster on local.
    dsn = build_tidb_dsn(host="localhost", username="root", password="password")
    assert str(dsn) == "mysql+pymysql://root:password@localhost:4000/test"
