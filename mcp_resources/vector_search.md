---
title: TiDB Vector Search
summary: Learn about Vector Search in TiDB. This feature provides an advanced search solution for performing semantic similarity searches across various data types, including documents, images, audio, and video.
---

# Vector Operations

TiDB supports the following vector operations:

- `VEC_COSINE_DISTANCE`: Calculate cosine similarity (most commonly used)
- `VEC_L2_DISTANCE`: Calculate Euclidean distance
- `VEC_L1_DISTANCE`: Calculate Manhattan distance
- `VEC_NEGATIVE_INNER_PRODUCT`: Calculate negative inner product
- `VEC_L2_NORM`: Calculate L2 norm
- `VEC_DIMS`: Get vector dimensions

# Usage Examples

## 1. Creating a Vector Table

Create a table with a vector column and a vector index:

```sql
CREATE TABLE documents (
    id INT PRIMARY KEY,
    embedding VECTOR(5),
    VECTOR INDEX idx_embedding ((VEC_COSINE_DISTANCE(embedding)))
);
```

**Notes**

- Cosine similarity is the recommended metric for most similarity search use cases
- HNSW index supports both `VEC_COSINE_DISTANCE` and `VEC_L2_DISTANCE` functions
- Vector dimensions must be specified when the column need to be indexed

## 2. Inserting Vector Data

```sql
INSERT INTO documents VALUES 
    (1, 'dog', '[1,2,1]'), 
    (2, 'cat', '[1,2,3]');
```

## 3. Performing Vector Search

Search for similar vectors using cosine similarity:

```sql
SELECT id, document, 
    1 - VEC_COSINE_DISTANCE(embedding, '[1,2,3]') AS similarity
FROM documents
ORDER BY similarity DESC
LIMIT 3;
```

