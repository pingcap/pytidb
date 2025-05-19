# Working with Tables

Compare to "Collection" and "Points" concepts in other vector databases, TiDB uses "Table" to represent a collection of data and provides flexibility to define the table structure based on your needs.

A table can contain multiple columns with various data types, including text, numbers, vectors, binary data (BLOB), JSON, and more.

## Create a table

### From TableModel

TiDB `TableModel` is based on [SQLModel](https://sqlmodel.tiangolo.com/), which is compatible with [Pydantic Model] and provides a declarative way to define the structure of a database table.

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

Once the table is created, you can use the `table` object to insert, update, delete, query, and search data, please refer to [CRUD Operations](./crud.md) for more details.

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
