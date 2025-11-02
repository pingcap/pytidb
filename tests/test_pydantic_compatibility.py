"""Tests for pydantic compatibility across different versions."""

import warnings
import pytest
from unittest.mock import patch

from pytidb.embeddings.base import BaseEmbeddingFunction, EmbeddingSourceType
from pytidb.search import SearchResult
from pytidb.result import SQLExecuteResult, SQLModelQueryResult
from pytidb.schema import VectorField


class MockEmbeddingFunction(BaseEmbeddingFunction):
    """Mock embedding function for testing."""

    def get_query_embedding(self, query, source_type: EmbeddingSourceType = "text", **kwargs):
        return [0.1, 0.2, 0.3]

    def get_source_embedding(self, source, source_type: EmbeddingSourceType = "text", **kwargs):
        return [0.1, 0.2, 0.3]

    def get_source_embeddings(self, sources, source_type: EmbeddingSourceType = "text", **kwargs):
        return [[0.1, 0.2, 0.3] for _ in sources]


class MockTableModel:
    """Mock table model for testing SearchResult."""

    def __init__(self, id: int, name: str):
        self.id = id
        self.name = name


class TestPydanticCompatibility:
    """Test pydantic compatibility across versions 2.0.3, 2.5.3, 2.10.6, 2.12.3."""

    def test_base_embedding_function_no_warnings(self):
        """Test BaseEmbeddingFunction doesn't raise protected namespace warnings."""
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")

            # Create embedding function with model_name field
            embedding_fn = MockEmbeddingFunction(
                provider="openai",
                model_name="text-embedding-3-small",
                dimensions=1536
            )

            # Assert no warnings about protected namespaces
            pydantic_warnings = [warning for warning in w if "protected namespace" in str(warning.message).lower()]
            assert len(pydantic_warnings) == 0, f"Got pydantic warnings: {[str(w.message) for w in pydantic_warnings]}"

            # Verify the model works correctly
            assert embedding_fn.provider == "openai"
            assert embedding_fn.model_name == "text-embedding-3-small"
            assert embedding_fn.dimensions == 1536

    def test_base_embedding_function_serialization(self):
        """Test BaseEmbeddingFunction serialization works correctly."""
        embedding_fn = MockEmbeddingFunction(
            provider="openai",
            model_name="text-embedding-3-small",
            dimensions=1536,
            use_server=True,
            additional_json_options={"param1": "value1"}
        )

        # Test serialization (standard pydantic v2 method)
        data = embedding_fn.model_dump()
        assert data["provider"] == "openai"
        assert data["model_name"] == "text-embedding-3-small"
        assert data["dimensions"] == 1536
        assert data["use_server"] is True
        assert data["additional_json_options"] == {"param1": "value1"}

        # Test deserialization
        new_fn = MockEmbeddingFunction.model_validate(data)
        assert new_fn.provider == "openai"
        assert new_fn.model_name == "text-embedding-3-small"
        assert new_fn.dimensions == 1536

    def test_search_result_with_generic_types(self):
        """Test SearchResult works with generic types across pydantic versions."""
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")

            # Create mock table model
            mock_hit = MockTableModel(id=1, name="test")

            # Create SearchResult with generic type
            result = SearchResult[MockTableModel](
                hit=mock_hit,
                distance=0.5,
                match_score=0.8,
                score=0.9
            )

            # Assert no warnings
            assert len(w) == 0, f"Got warnings: {[str(warning.message) for warning in w]}"

            # Verify functionality
            assert result.hit.id == 1
            assert result.hit.name == "test"
            assert result.distance == 0.5
            assert result.match_score == 0.8
            assert result.score == 0.9
            assert result.similarity_score == 0.5  # 1 - distance

    def test_search_result_attribute_delegation(self):
        """Test SearchResult properly delegates attributes to hit object."""
        mock_hit = MockTableModel(id=42, name="test_item")
        result = SearchResult[MockTableModel](hit=mock_hit)

        # Test attribute delegation
        assert result.id == 42
        assert result.name == "test_item"

        # Test error for non-existent attribute
        with pytest.raises(AttributeError):
            _ = result.non_existent_attribute

    def test_sql_execute_result(self):
        """Test SQLExecuteResult pydantic model."""
        result = SQLExecuteResult(
            rowcount=5,
            success=True,
            message="Operation completed successfully"
        )

        assert result.rowcount == 5
        assert result.success is True
        assert result.message == "Operation completed successfully"

        # Test serialization
        data = result.model_dump()
        assert data["rowcount"] == 5
        assert data["success"] is True
        assert data["message"] == "Operation completed successfully"

    def test_sql_model_query_result(self):
        """Test SQLModelQueryResult with pydantic models."""
        # Create mock BaseModel instances
        from pydantic import BaseModel

        class TestModel(BaseModel):
            id: int
            name: str

        models = [
            TestModel(id=1, name="first"),
            TestModel(id=2, name="second")
        ]

        result = SQLModelQueryResult(models)

        # Test to_list method (uses model_dump)
        list_data = result.to_list()
        expected = [{"id": 1, "name": "first"}, {"id": 2, "name": "second"}]
        assert list_data == expected

        # Test to_pydantic method
        pydantic_data = result.to_pydantic()
        assert len(pydantic_data) == 2
        assert pydantic_data[0].id == 1
        assert pydantic_data[0].name == "first"

    def test_vector_field_with_embedding_function(self):
        """Test VectorField creation with embedding function."""
        embedding_fn = MockEmbeddingFunction(
            provider="openai",
            model_name="text-embedding-3-small",
            dimensions=1536
        )

        # Test VectorField creation through embedding function
        vector_field = embedding_fn.VectorField(
            source_field="content",
            source_type="text"
        )

        # VectorField returns sqlmodel.FieldInfo, metadata is in _attributes_set
        attributes = vector_field._attributes_set
        assert attributes["embed_fn"] == embedding_fn
        assert attributes["dimensions"] == 1536
        assert attributes["source_field"] == "content"
        assert attributes["source_type"] == "text"

    def test_model_config_settings(self):
        """Test that ConfigDict settings are properly applied."""
        # Test BaseEmbeddingFunction protected_namespaces setting (selective protection)
        embedding_fn = MockEmbeddingFunction(model_name="test-model")
        config = embedding_fn.model_config
        protected_namespaces = config.get("protected_namespaces", ())
        # Should protect critical methods but allow model_name
        expected_protections = {"model_dump", "model_copy", "model_validate", "model_fields", "model_config"}
        assert expected_protections.issubset(set(protected_namespaces))

        # Test SearchResult arbitrary_types_allowed setting
        mock_hit = MockTableModel(id=1, name="test")
        result = SearchResult[MockTableModel](hit=mock_hit)
        config = result.model_config
        assert config.get("arbitrary_types_allowed") is True


class TestEdgeCases:
    """Test edge cases for pydantic compatibility."""

    def test_embedding_function_with_none_values(self):
        """Test embedding function with None values for optional fields."""
        embedding_fn = MockEmbeddingFunction(
            provider="custom",
            model_name=None,  # This should not cause issues
            dimensions=None,
            additional_json_options=None
        )

        assert embedding_fn.provider == "custom"
        assert embedding_fn.model_name is None
        assert embedding_fn.dimensions is None
        assert embedding_fn.additional_json_options is None

    def test_search_result_with_none_scores(self):
        """Test SearchResult with None values for optional score fields."""
        mock_hit = MockTableModel(id=1, name="test")
        result = SearchResult[MockTableModel](
            hit=mock_hit,
            distance=None,
            match_score=None,
            score=None
        )

        assert result.distance is None
        assert result.match_score is None
        assert result.score is None
        assert result.similarity_score is None  # Since distance is None

    def test_backward_compatibility_regression(self):
        """Test that the critical backward compatibility regression is fixed."""
        embedding_fn = MockEmbeddingFunction(
            provider="openai",
            model_name="foo/bar",
            dimensions=1
        )

        # Test 1: model_dump() should return model_name in the output
        data = embedding_fn.model_dump()
        assert "model_name" in data
        assert data["model_name"] == "foo/bar"
        assert "embedding_model" not in data  # Should not have internal field name

        # Test 2: model_copy(update={"model_name": "new"}) should work
        updated = embedding_fn.model_copy(update={"model_name": "baz"})
        assert updated.model_name == "baz"
        assert updated.model_name != embedding_fn.model_name  # Should be different from original

        # Test 3: Round-trip serialization should work
        new_instance = MockEmbeddingFunction.model_validate(data)
        assert new_instance.model_name == "foo/bar"

    def test_method_shadowing_protection(self):
        """Test that protected namespaces prevent method shadowing."""
        with pytest.raises(ValueError, match="conflicts with member"):
            class BadEmbedding(MockEmbeddingFunction):
                model_dump: str = "boom"  # This should be rejected

    def test_sql_execute_result_defaults(self):
        """Test SQLExecuteResult with default values."""
        result = SQLExecuteResult()

        assert result.rowcount == 0
        assert result.success is False
        assert result.message is None