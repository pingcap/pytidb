# Vector Search

Vector search uses semantic similarity to help you find the most relevant records, even if your query does not explicitly include all the keywords. The query will be embedded automatically.

## Distance metrics

Distance metrics are a measure of the similarity between a pair of vectors. Currently, TiDB supports the following metrics:

=== "Python"

    | Metric     | Description                                                             | Typical Use Case          |
    |------------|-------------------------------------------------------------------------|---------------------------|
    | `COSINE`   | [Cosine similarity](https://en.wikipedia.org/wiki/Cosine_similarity)    | Text, semantic similarity |
    | `L2`       | [Euclidean distance ](https://en.wikipedia.org/wiki/Euclidean_distance) | Image search              |


=== "SQL"

    In SQL, you can use the following built-in functions to calculate vector distances directly in your queries:

    | Function Name                                                                                                                        | Description                                                    |
    |-------------------------------------------------------------------------------------------------------------------------------------|----------------------------------------------------------------|
    | [`VEC_L2_DISTANCE`](https://docs.pingcap.com/tidbcloud/vector-search-functions-and-operators/#vec_l2_distance)                       | Calculates L2 distance (Euclidean distance) between two vectors |
    | [`VEC_COSINE_DISTANCE`](https://docs.pingcap.com/tidbcloud/vector-search-functions-and-operators/#vec_cosine_distance)               | Calculates the cosine distance between two vectors              |
    | [`VEC_NEGATIVE_INNER_PRODUCT`](https://docs.pingcap.com/tidbcloud/vector-search-functions-and-operators/#vec_negative_inner_product) | Calculates the negative of the inner product between two vectors|
    | [`VEC_L1_DISTANCE`](https://docs.pingcap.com/tidbcloud/vector-search-functions-and-operators/#vec_l1_distance)                       | Calculates L1 distance (Manhattan distance) between two vectors |


## Basic Usage

=== "Python"

    You can use the `table.search()` method to perform searches, which uses `search_mode="vector"` by default.

    For example:

    ```python hl_lines="17"
    from pytidb.schema import TableModel, Field, VectorField

    class Chunk(TableModel, table=True):
        __table__ = "chunks"

        id: int = Field(primary_key=True)
        text: str = Field()
        text_vec: list[float] = VectorField(dimension=3)

    table = db.create_table(schema=Chunk)
    table.bulk_insert([
        Chunk(text="dog", text_vec=[1,2,1]),
        Chunk(text="fish", text_vec=[1,2,4]),
        Chunk(text="tree", text_vec=[1,0,0]),
    ])

    res = table.search([1, 2, 3]).limit(3).to_list()

    print(res)
    ```

=== "SQL"

    You can use the `ORDER BY vec_cosine_distance(column_name, query_vector)` function to get the nearest neighbors of the query vector.

    For example, assuming you have created the following `chunks` table:

    ```sql hl_lines="12-15"
    CREATE TABLE chunks (
        id INT PRIMARY KEY,
        text VARCHAR(255),
        text_vec VECTOR(3)
    );

    INSERT INTO chunks (id, text, text_vec) VALUES
        (1, 'dog', '[1,2,1]'),
        (2, 'fish', '[1,2,4]'),
        (3, 'tree', '[1,0,0]');

    SELECT id, text, vec_cosine_distance(text_vec, '[1,2,3]') AS distance
    FROM chunks
    ORDER BY distance
    LIMIT 3;
    ```

    The result will be:

    ```python
    +----+----------+---------------------+
    | id | document | distance            |
    +----+----------+---------------------+
    |  2 | fish     | 0.00853986601633272 |
    |  1 | dog      | 0.12712843905603044 |
    |  3 | tree     |  0.7327387580875756 |
    +----+----------+---------------------+
    3 rows in set (0.15 sec)
    ```

## Output search results

The search results can be returned in several formats:

### As SQLAlchemy result rows

If you want to work with the raw SQLAlchemy result rows, you can use:

```python
table.search([1, 2, 3]).to_rows()
```

### As a list of Python dicts

For easier manipulation in Python, you can convert the results to a list of dictionaries:

```python
table.search([1, 2, 3]).to_list()
```

### As a pandas DataFrame

To display the results in a user-friendly table—especially useful in Jupyter notebooks—you can convert them to a pandas DataFrame:

```python
table.search([1, 2, 3]).to_pandas()
```




