# Connect to database

In this guide, we will introduce how to connect to a TiDB database using the TiDB client.

## Install the dependencies

[pytidb](https://github.com/pingcap/pytidb) is a Python client built upon [SQLAlchemy](https://sqlalchemy.org/), it provides a series of high-level APIs to help developers store and search vector embeddings without writing raw SQL.

To install the Python client, run the following command:

```bash
pip install pytidb
```

## Connect with connection parameters

Choose the steps based on your deployment type:

=== "TiDB Cloud Serverless"

    You can create a serverless cluster in the [TiDB Cloud](https://tidbcloud.com/free-trial/), and then get the connection parameters from the web console.

    1. Navigate to the [Clusters page](https://tidbcloud.com/clusters), and then click the name of your target cluster to go to its overview page.
    2. Click **Connect** in the upper-right corner. A connection dialog is displayed, with connection parameters listed.
    3. Copy the connection parameters to your code or environment variables.

    Example code:

    ```python title="main.py"
    from pytidb import TiDBClient

    db = TiDBClient.connect(
        host="{gateway-region}.prod.aws.tidbcloud.com",
        port=4000,
        username="{prefix}.root",
        password="{password}",
        database="test",
    )
    ```

    !!! tip

        For TiDB Cloud Serverless, [TLS connection to the database](https://docs.pingcap.com/tidbcloud/secure-connections-to-serverless-clusters/) is required when using Public Endpoint. TiDB Client will **automatically** enable TLS connection for serverless clusters.

=== "TiDB Self-Managed"

    You can follow [Quick Start with TiDB Self-Managed](https://docs.pingcap.com/tidb/stable/quick-start-with-tidb/#deploy-a-local-test-cluster) to deploy a TiDB cluster for testing.

    Example code:

    ```python title="main.py"
    from pytidb import TiDBClient

    db = TiDBClient.connect(
        host="{tidb_server_host}",
        port=4000,
        username="root",
        password="{password}",
        database="test",
    )
    ```

    !!! tip
    
        If you are using `tiup playground` to deploy a TiDB cluster for testing, the default host is `127.0.0.1` and the default password is empty.

Once connected, you can use the `db` object to operate tables, query data, and more.

## Connect with connection string

If you prefer to use a connection string (database URL), you can follow the format based on your deployment type:

=== "TiDB Cloud Serverless"

    You can create a serverless cluster in the [TiDB Cloud](https://tidbcloud.com/free-trial/), and then get the connection parameters from the web console.

    1. Navigate to the [Clusters page](https://tidbcloud.com/clusters), and then click the name of your target cluster to go to its overview page.
    2. Click **Connect** in the upper-right corner. A connection dialog is displayed with the connection parameters listed.
    3. Copy the connection parameters and construct the connection string as the format below.

    ```python title="main.py"
    from pytidb import TiDBClient

    db = TiDBClient.connect(
        database_url="mysql+pymysql://{USERNAME}:{PASSWORD}@{HOST}:{PORT}/{DATABASE}?ssl_verify_cert=true&ssl_verify_identity=true",
    )
    ```

    !!! note
    
        For TiDB Cloud Serverless, [TLS connection to the database](https://docs.pingcap.com/tidbcloud/secure-connections-to-serverless-clusters/) is required when using Public Endpoint, so you need to set `ssl_verify_cert=true&ssl_verify_identity=true` in the connection string.

=== "TiDB Self-Managed"

    You can follow the format below to construct the connection string:

    ```python title="main.py"
    from pytidb import TiDBClient

    db = TiDBClient.connect(
        database_url="mysql+pymysql://{USERNAME}:{PASSWORD}@{HOST}:{PORT}/{DATABASE}",
    )
    ```

    !!! tip

        If you are using `tiup playground` to deploy a TiDB cluster for testing, the connection string is: 
        
        ```
        mysql+pymysql://root:@127.0.0.1:4000/test
        ```

## Connect with SQLAlchemy DB engine

If your application already has an existing SQLAlchemy database engine, you can reuse the engine through the `db_engine` parameter:

```python title="main.py"
from pytidb import TiDBClient

db = TiDBClient(db_engine=db_engine)
```

## Next Steps

After connecting to your TiDB database, you can explore the following guides to learn how to work with your data:

- [Working with Tables](./tables.md): Learn how to define and manage tables in TiDB.
- [Basic CRUD Operations](./crud.md): Insert, query, update, and delete data in your tables.
- [Vector Search](./vector-search.md): Perform semantic search using vector embeddings.
- [Fulltext Search](./fulltext-search.md): Retrieve documents using keyword-based search.
- [Hybrid Search](./hybrid-search.md): Combine vector and full-text search for more relevant results.
