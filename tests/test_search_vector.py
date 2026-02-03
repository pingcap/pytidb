import os
from typing import Any

import pytest
from pydantic import BaseModel

from pytidb import TiDBClient, Table
from pytidb.orm.indexes import VectorIndex
from pytidb.rerankers import Reranker
from pytidb.rerankers.base import BaseReranker
from pytidb.schema import DistanceMetric, TableModel, Field, Column, Relationship
from pytidb.sql import or_
from pytidb.datatype import VECTOR, JSON
from pytidb.search import SCORE_LABEL

from tests.utils import normalize_sql


# Vector Search


@pytest.fixture(scope="module")
def vector_table(shared_client: TiDBClient):
    class UserForVectorSearch(TableModel):
        __tablename__ = "users_for_vector_search"
        id: int = Field(None, primary_key=True)
        name: str = Field(None)

    User = UserForVectorSearch
    user_table = shared_client.create_table(schema=User, if_exists="overwrite")

    class ChunkForVectorSearch(TableModel):
        __tablename__ = "chunks_for_vector_search"
        __table_args__ = (VectorIndex("vec_idx_text_vec_cosine", "text_vec"),)
        id: int = Field(None, primary_key=True)
        text: str = Field(None)
        text_vec: Any = Field(sa_column=Column(VECTOR(3)))
        user_id: int = Field(foreign_key="users_for_vector_search.id")
        user: UserForVectorSearch = Relationship(
            sa_relationship_kwargs={
                "primaryjoin": "ChunkForVectorSearch.user_id == UserForVectorSearch.id",
                "lazy": "joined",
            },
        )
        meta: dict = Field(sa_type=JSON)

    Chunk = ChunkForVectorSearch
    chunk_table = shared_client.create_table(schema=Chunk, if_exists="overwrite")

    # Prepare test data.
    user_table.bulk_insert(
        [
            User(id=1, name="tom"),
            User(id=2, name="jerry"),
            User(id=3, name="bob"),
        ]
    )
    chunk_table.bulk_insert(
        [
            Chunk(
                id=1, text="foo", text_vec=[4, 5, 6], user_id=1, meta={"owner_id": 1}
            ),
            Chunk(
                id=2, text="bar", text_vec=[1, 2, 3], user_id=2, meta={"owner_id": 2}
            ),
            Chunk(
                id=3, text="biz", text_vec=[7, 8, 9], user_id=3, meta={"owner_id": 3}
            ),
        ]
    )

    return chunk_table


def test_vector_search(vector_table: Table):
    # to_pydantic()
    results = (
        vector_table.search([1, 2, 3])
        .distance_metric(metric=DistanceMetric.L2)
        .num_candidate(20)
        .filter({"user_id": 2}, prefilter=True)
        .limit(2)
        .to_pydantic()
    )
    assert len(results) == 1
    assert results[0].text == "bar"
    assert results[0].similarity_score == 1
    assert results[0].score == 1
    assert results[0].user_id == 2
    assert results[0].user.name == "jerry"

    # to_pandas()
    results = vector_table.search([1, 2, 3]).limit(2).to_pandas()
    assert results.size > 0

    # to_list()
    results = vector_table.search([1, 2, 3]).limit(2).to_list()
    assert len(results) > 0
    assert results[0]["text"] == "bar"
    assert results[0][SCORE_LABEL] == 1
    assert results[0]["user_id"] == 2
    assert results[0]["_distance"] == 0
    assert results[0]["_score"] == 1


def test_with_distance_threshold(vector_table: Table):
    result = (
        vector_table.search([1, 2, 3])
        .debug()
        .distance_threshold(0.01)
        .limit(10)
        .to_list()
    )
    assert len(result) == 1


def test_with_distance_range(vector_table: Table):
    results = (
        vector_table.search([1, 2, 3]).distance_range(0.02, 0.05).limit(10).to_list()
    )

    assert len(results) == 2
    assert results[0]["id"] == 1
    assert results[0]["text"] == "foo"
    assert results[0]["user_id"] == 1
    assert abs(results[0]["_distance"] - 0.0254) < 1e-3

    assert results[1]["id"] == 3
    assert results[1]["text"] == "biz"
    assert results[1]["user_id"] == 3
    assert abs(results[1]["_distance"] - 0.0408) < 1e-3


@pytest.mark.parametrize("prefilter", [True, False], ids=["prefilter", "postfilter"])
def test_with_dict_filter(vector_table: Table, prefilter: bool):
    results = (
        vector_table.search([1, 2, 3])
        .distance_metric(metric=DistanceMetric.COSINE)
        .debug(True)
        .filter({"user_id": {"$in": [1, 2]}}, prefilter=prefilter)
        .limit(10)
        .to_list()
    )

    assert len(results) == 2
    assert results[0]["id"] == 2
    assert results[0]["text"] == "bar"
    assert results[0]["user_id"] == 2
    assert results[0]["_distance"] == 0
    assert results[0]["_score"] == 1

    assert results[1]["id"] == 1
    assert results[1]["text"] == "foo"
    assert results[1]["user_id"] == 1
    assert abs(results[1]["_distance"] - 0.02547) < 1e-3
    assert abs(results[1]["_score"] - 0.97463) < 1e-3


@pytest.mark.parametrize("prefilter", [True, False], ids=["prefilter", "postfilter"])
def test_with_expression_filter(vector_table: Table, prefilter: bool):
    Chunk = vector_table.table_model

    def assert_result(results):
        assert len(results) == 2
        assert results[0]["id"] == 2
        assert results[0]["text"] == "bar"
        assert results[0]["user_id"] == 2
        assert results[0]["_distance"] == 0
        assert results[0]["_score"] == 1

        assert results[1]["id"] == 1
        assert results[1]["text"] == "foo"
        assert results[1]["user_id"] == 1
        assert abs(results[1]["_distance"] - 0.02547) < 1e-3
        assert abs(results[1]["_score"] - 0.97463) < 1e-3

    # user_id in (1, 2)
    results = (
        vector_table.search([1, 2, 3])
        .filter(
            Chunk.user_id.in_([1, 2]),
            prefilter=prefilter,
        )
        .limit(10)
        .to_list()
    )
    assert_result(results)

    # user_id = 1 or user_id = 2
    results = (
        vector_table.search([1, 2, 3])
        .filter(
            or_(Chunk.user_id == 1, Chunk.user_id == 2),
            prefilter=prefilter,
        )
        .limit(10)
        .to_list()
    )
    assert_result(results)


@pytest.mark.parametrize("prefilter", [True, False], ids=["prefilter", "postfilter"])
def test_with_metadata_filter(vector_table: Table, prefilter: bool):
    results = (
        vector_table.search([1, 2, 3])
        .distance_metric(metric=DistanceMetric.COSINE)
        .debug(True)
        .filter({"meta.owner_id": {"$in": [1, 2]}}, prefilter=prefilter)
        .limit(10)
        .to_list()
    )

    assert len(results) == 2
    assert results[0]["id"] == 2
    assert results[0]["text"] == "bar"
    assert results[0]["user_id"] == 2
    assert results[0]["_distance"] == 0
    assert results[0]["_score"] == 1

    assert results[1]["id"] == 1
    assert results[1]["text"] == "foo"
    assert results[1]["user_id"] == 1
    assert abs(results[1]["_distance"] - 0.02547) < 1e-3
    assert abs(results[1]["_score"] - 0.97463) < 1e-3


@pytest.mark.parametrize("prefilter", [True, False], ids=["prefilter", "postfilter"])
def test_with_text_filter(vector_table: Table, prefilter: bool):
    results = (
        vector_table.search([1, 2, 3])
        .distance_metric(metric=DistanceMetric.COSINE)
        .debug(True)
        .filter("user_id in (1, 2)")
        .limit(10)
        .to_list()
    )

    assert len(results) == 2
    assert results[0]["id"] == 2
    assert results[0]["text"] == "bar"
    assert results[0]["user_id"] == 2
    assert results[0]["_distance"] == 0
    assert results[0]["_score"] == 1

    assert results[1]["id"] == 1
    assert results[1]["text"] == "foo"
    assert results[1]["user_id"] == 1
    assert abs(results[1]["_distance"] - 0.02547) < 1e-3
    assert abs(results[1]["_score"] - 0.97463) < 1e-3


@pytest.mark.parametrize("prefilter", [True, False], ids=["prefilter", "postfilter"])
def test_with_filter_and_distance_threshold(vector_table: Table, prefilter: bool):
    """Test prefilter with distance threshold."""
    results = (
        vector_table.search([1, 2, 3])
        .distance_threshold(0.03)  # Only Chunk #1 and #2 are within the threshold.
        .filter(
            {"user_id": 1}, prefilter=prefilter
        )  # Filter on user_id=1, only Chunk #1 is left.
        .limit(10)
        .to_list()
    )

    assert len(results) == 1
    assert results[0]["id"] == 1
    assert results[0]["text"] == "foo"
    assert results[0]["user_id"] == 1
    assert abs(results[0]["_distance"] - 0.0254) < 1e-3


@pytest.mark.parametrize("prefilter", [True, False], ids=["prefilter", "postfilter"])
def test_with_filter_and_distance_range(vector_table: Table, prefilter: bool):
    results = (
        vector_table.search([1, 2, 3])
        .distance_range(0.02, 0.05)  # Chunk #1 and #3 are within the range.
        .filter(
            {"user_id": 1}, prefilter=prefilter
        )  # Filter on user_id=1, only Chunk #1 is left.
        .limit(10)
        .to_list()
    )

    assert len(results) == 1
    assert results[0]["id"] == 1
    assert results[0]["text"] == "foo"
    assert results[0]["user_id"] == 1
    assert abs(results[0]["_distance"] - 0.0254) < 1e-3


@pytest.fixture(scope="module")
def reranker():
    return Reranker(
        model_name="jina_ai/jina-reranker-v2-base-multilingual",
        api_key=os.getenv("JINA_AI_API_KEY"),
    )


def test_rerank(vector_table: Table, reranker: BaseReranker):
    reranked_results = (
        vector_table.search(search_type="vector")
        .vector([1, 2, 3])
        .text("bar")
        .rerank(reranker, "text")
        .limit(3)
        .to_list()
    )

    assert len(reranked_results) > 0
    assert reranked_results[0]["text"] == "bar"
    assert reranked_results[0]["_score"] > 0


def test_with_multi_vector_fields(shared_client: TiDBClient):
    class ChunkWithMultiVec(TableModel):
        __tablename__ = "test_vector_search_multi_vec"
        id: int = Field(None, primary_key=True)
        title: str = Field(None)
        title_vec: list[float] = Field(sa_column=Column(VECTOR(3)))
        body: str = Field(None)
        body_vec: list[float] = Field(sa_column=Column(VECTOR(3)))

    tbl = shared_client.create_table(schema=ChunkWithMultiVec, if_exists="overwrite")
    tbl.bulk_insert(
        [
            ChunkWithMultiVec(
                id=1, title="tree", title_vec=[4, 5, 6], body="cat", body_vec=[1, 2, 3]
            ),
            ChunkWithMultiVec(
                id=2, title="grass", title_vec=[1, 2, 3], body="dog", body_vec=[7, 8, 9]
            ),
            ChunkWithMultiVec(
                id=3, title="leaf", title_vec=[7, 8, 9], body="bird", body_vec=[4, 5, 6]
            ),
        ]
    )

    with pytest.raises(ValueError, match="more than one vector column"):
        tbl.search([1, 2, 3], search_type="vector").limit(3).to_list()

    with pytest.raises(ValueError, match="Invalid vector column"):
        tbl.search([1, 2, 3], search_type="vector").vector_column("title").limit(3)

    with pytest.raises(ValueError, match="Non-exists vector column"):
        tbl.search([1, 2, 3], search_type="vector").vector_column(
            "non_exist_column"
        ).limit(3)

    with pytest.raises(ValueError, match="Invalid vector column name"):
        tbl.search([1, 2, 3], search_type="vector").vector_column(None).limit(3)

    results = (
        tbl.search([1, 2, 3], search_type="vector")
        .vector_column("title_vec")
        .limit(3)
        .to_list()
    )
    assert len(results) == 3
    assert results[0]["id"] == 2
    assert results[0]["title"] == "grass"
    assert results[0]["_distance"] == 0
    assert results[0]["_score"] == 1

    results = (
        tbl.search([1, 2, 3], search_type="vector")
        .vector_column("body_vec")
        .limit(3)
        .to_list()
    )
    assert len(results) == 3
    assert results[0]["id"] == 1
    assert results[0]["body"] == "cat"
    assert results[0]["_distance"] == 0
    assert results[0]["_score"] == 1


# ================================
# Skip Null Vectors SQL Test Cases
# ================================

class SkipNullVectorsSqlTestCase(BaseModel):
    """Test case for vector search SQL with skip_null_vectors and prefilter/postfilter."""

    id: str
    prefilter: bool
    skip_null_vectors_flag: bool
    expected_sql: str


SKIP_NULL_VECTORS_SQL_TEST_CASES = [
    SkipNullVectorsSqlTestCase(
        id="prefilter_skip_null_true",
        prefilter=True,
        skip_null_vectors_flag=True,
        expected_sql="""
            SELECT
                _hit.id,
                _hit.text,
                _hit.text_vec,
                _hit.user_id,
                _hit.meta,
                VEC_COSINE_DISTANCE(_hit.text_vec, '[1, 2, 3]') AS _distance,
                1 - VEC_COSINE_DISTANCE(_hit.text_vec, '[1, 2, 3]') AS _score,
                users_for_vector_search_1.id AS id_1,
                users_for_vector_search_1.name
            FROM chunks_for_vector_search AS _hit
            LEFT OUTER JOIN users_for_vector_search AS users_for_vector_search_1
                ON _hit.user_id = users_for_vector_search_1.id
            WHERE _hit.user_id = 1
            HAVING _distance IS NOT NULL
            ORDER BY _distance ASC
            LIMIT 5
            """,
    ),
    SkipNullVectorsSqlTestCase(
        id="postfilter_skip_null_true",
        prefilter=False,
        skip_null_vectors_flag=True,
        expected_sql="""
            SELECT
                candidates.id,
                candidates.text,
                candidates.text_vec,
                candidates.user_id,
                candidates.meta,
                candidates._distance,
                1 - candidates._distance AS _score,
                users_for_vector_search_1.id AS id_1,
                users_for_vector_search_1.name
            FROM (
                SELECT
                    _inner_hit.id AS id,
                    _inner_hit.text AS text,
                    _inner_hit.text_vec AS text_vec,
                    _inner_hit.user_id AS user_id,
                    _inner_hit.meta AS meta,
                    VEC_COSINE_DISTANCE(_inner_hit.text_vec, '[1, 2, 3]') AS _distance
                FROM chunks_for_vector_search AS _inner_hit
                ORDER BY _distance ASC
                LIMIT 50
            ) AS candidates
            LEFT OUTER JOIN users_for_vector_search AS users_for_vector_search_1
                ON candidates.user_id = users_for_vector_search_1.id
            WHERE candidates.user_id = 1 AND candidates._distance IS NOT NULL
            ORDER BY candidates._distance ASC
            LIMIT 5
            """,
    ),
    SkipNullVectorsSqlTestCase(
        id="postfilter_skip_null_false",
        prefilter=False,
        skip_null_vectors_flag=False,
        expected_sql="""
            SELECT
                candidates.id,
                candidates.text,
                candidates.text_vec,
                candidates.user_id,
                candidates.meta,
                candidates._distance,
                1 - candidates._distance AS _score,
                users_for_vector_search_1.id AS id_1,
                users_for_vector_search_1.name
            FROM (
                SELECT
                    _inner_hit.id AS id,
                    _inner_hit.text AS text,
                    _inner_hit.text_vec AS text_vec,
                    _inner_hit.user_id AS user_id,
                    _inner_hit.meta AS meta,
                    VEC_COSINE_DISTANCE(_inner_hit.text_vec, '[1, 2, 3]') AS _distance
                FROM chunks_for_vector_search AS _inner_hit
                ORDER BY _distance ASC
                LIMIT 50
            ) AS candidates
            LEFT OUTER JOIN users_for_vector_search AS users_for_vector_search_1
                ON candidates.user_id = users_for_vector_search_1.id
            ORDER BY candidates._distance ASC
            LIMIT 5
            """,
    ),
]


@pytest.mark.parametrize(
    "case",
    SKIP_NULL_VECTORS_SQL_TEST_CASES,
    ids=[c.id for c in SKIP_NULL_VECTORS_SQL_TEST_CASES],
)
def test_skip_null_vectors_sql(vector_table: Table, case: SkipNullVectorsSqlTestCase) -> None:
    """Assert the full compiled SQL for vector search with skip_null_vectors and prefilter/postfilter."""
    if case.prefilter or case.skip_null_vectors_flag:
        search = (
            vector_table.search([1, 2, 3])
            .skip_null_vectors(case.skip_null_vectors_flag)
            .filter({"user_id": 1}, prefilter=case.prefilter)
            .limit(5)
        )
    else:
        search = vector_table.search([1, 2, 3]).skip_null_vectors(False).limit(5)
    stmt = search._build_vector_query()
    compiled = stmt.compile(
        dialect=search._table.db_engine.dialect,
        compile_kwargs={"literal_binds": True},
    )
    actual_sql = normalize_sql(str(compiled))
    assert actual_sql == normalize_sql(case.expected_sql)

    # For postfilter, inner query is KNN-first so TiDB can use vector index.
    # Prefilter (WHERE before ORDER BY) cannot use vector index per TiDB semantics.
    if not case.prefilter:
        explain_sql = f"EXPLAIN ANALYZE {actual_sql}"
        plan_result = vector_table.client.query(explain_sql).to_list()
        plan_text = " ".join(str(v) for row in plan_result for v in row.values())
        assert "annIndex" in plan_text and "COSINE" in plan_text, (
            f"Expected execution plan to use vector index (annIndex:COSINE), got: {plan_text}"
        )
