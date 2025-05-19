# Basic CRUD Operations

This guide will walk you through the basic CRUD operations for tables.

!!! tip

    To check the complete example, please refer to the [example](https://github.com/pingcap/pytidb/tree/main/examples/basic).

## Add data to a table

Use the `insert()` method to insert records into the table.

### With TableModel

You can using a `TableModel` instance to represent a record and insert it into the table.

Insert a single record:

=== "Python"

```python
table.insert(
    Chunk(
        text="TiDB is a distributed database that supports OLTP, OLAP, HTAP and AI workloads.",
        text_vec=[0.1, 0.2, 0.3],
        user_id=1
    )
)
```

Insert multiple records:

=== "Python"

```python
table.bulk_insert([
    Chunk(
        text="PyTiDB is a Python library for developers to connect to TiDB.",
        text_vec=[0.4, 0.5, 0.6],
        user_id=2
    ),
    Chunk(
        text="LlamaIndex is a framework for building AI applications.",
        text_vec=[0.7, 0.8, 0.9],
        user_id=2
    ),
])
```

## Query data from a table

Use the `query()` method to query data from a table.

=== "Python"

```python
table.query(
    filters={
        "user_id": 1
    }
)
```

## Update data in a table

Use the `update()` method to update the specified records with [filters](./filtering.md).

=== "Python"

```python
table.update(
    values={
        "text": "<new_value>",
        "text_vec": [0.2, 0.3, 0.4],
    },
    filters={
        "id": 1
    }
)
```

## Delete from a table

Use the `delete()` method to delete specified data records with [filters](./filtering.md).

=== "Python"

```python
table.delete(
    filters={
        "user_id": 2
    }
)
```
