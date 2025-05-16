# Working with Tables

Compare to "Collection" and "Points" concepts in other vector databases, TiDB uses "Table" to represent a collection of data and provides flexibility to define the table structure based on your needs.

A table can contain multiple columns with various data types, including text, numbers, vectors, binary data (BLOB), JSON, and more.

## Create a table

### From TableModel

[TableModel](./table-model.md) is compatible with [Pydantic Model](https://docs.pydantic.dev/latest/), you can define the structure of a database table using the `TableModel` class.

=== "Python"

    ```python
    from pytidb.schema import TableModel, Field, VectorField

    class Chunk(TableModel, table=True):
        __tablename__ = "chunks"

        id: int = Field(primary_key=True)
        text: str = Field()
        text_vec: list[float] = VectorField(dimension=3)
        user_id: int = Field()

    table = db.create_table(schema=Chunk)
    ```

Once the table is created, you can use the `table` object to insert, update, delete, query, and search data.

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

## Truncate table

Use the `truncate()` method on the table to clear all data in the table.

=== "Python"

```python
table.truncate()

# Check the table is truncated, should be 0 rows.
table.rows()
```

## Drop a table

Use the `db.drop_table()` method remove the specified table from the database.

=== "Python"

```python
db.drop_table("table_name")

# Check the table is removed from the database.
db.table_names()
```
