# Multiple Table Joins

As a relational database, TiDB allows you to store diverse data in tables with different structures (for example: `chunks`, `documents`, `users`, `chats`). It also supports multi-table JOINs, enabling you to combine data from different tables in a single query.


## Basic Usage

=== "Python"

    Assuming you have already [connected to the TiDB database](./connect.md) via TiDBClient:

    ```python
    from pytidb import TableModel, Field, Session
    from pytidb.sql import select

    class Document(TableModel, table=True):
        __tablename__ = "documents"
        id: int = Field(primary_key=True)
        title: str = Field(max_length=255)

    class Chunk(TableModel, table=True):
        __tablename__ = "chunks"
        id: int = Field(primary_key=True)
        text: str = Field(max_length=255)
        document_id: int = Field(foreign_key="documents.id")

    db.create_table(schema=Document)
    db.create_table(schema=Chunk)
    db.table("documents").truncate()
    db.table("chunks").truncate()
    db.table("documents").insert(Document(id=1, title="Alice"))
    db.table("chunks").insert(Chunk(id=1, text="Hello", document_id=1))

    db_engine = db.db_engine
    with Session(db_engine) as db_session:
        query = (
            select(Chunk)
            .join(Document, Chunk.document_id == Document.id)
            .where(Document.title == "Alice")
        )
        chunks = db_session.exec(query).all()

    [(c.id, c.text, c.document_id) for c in chunks]
    ```

=== "SQL"

    ```sql
    CREATE TABLE documents (
        id INT PRIMARY KEY,
        title VARCHAR(255) NOT NULL
    );

    CREATE TABLE chunks (
        id INT PRIMARY KEY,
        text VARCHAR(255) NOT NULL,
        document_id INT NOT NULL,
        FOREIGN KEY (document_id) REFERENCES documents(id)
    );
    ```

    ```sql
    SELECT c.id, c.text, c.document_id
    FROM chunks c
    JOIN documents d ON c.document_id = d.id
    WHERE d.title = 'Alice';
    ```
