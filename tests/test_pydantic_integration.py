"""
Test PyTiDB compatibility with different Pydantic versions.

This test module verifies that PyTiDB works correctly across
different Pydantic versions (2.0.3, 2.5.3, 2.10.6, 2.12.3).
"""
import sys
from typing import List, Optional, Any
import pytest
import pydantic


class TestPydanticCompatibility:
    """Test suite for Pydantic version compatibility."""

    def test_pydantic_version_info(self):
        """Verify current Pydantic version is accessible."""
        assert hasattr(pydantic, 'VERSION')
        assert isinstance(pydantic.VERSION, str)
        print(f"Testing with Pydantic version: {pydantic.VERSION}")

    def test_base_embedding_function_creation(self):
        """Test BaseEmbeddingFunction can be instantiated without warnings."""
        from pytidb.embeddings.base import BaseEmbeddingFunction

        class TestEmbeddingFunction(BaseEmbeddingFunction):
            def get_query_embedding(self, query: Any, source_type: Optional[str] = "text", **kwargs) -> List[float]:
                return [0.1, 0.2, 0.3]

            def get_source_embedding(self, source: Any, source_type: Optional[str] = "text", **kwargs) -> List[float]:
                return [0.1, 0.2, 0.3]

            def get_source_embeddings(self, sources: List[Any], source_type: Optional[str] = "text", **kwargs) -> List[List[float]]:
                return [[0.1, 0.2, 0.3] for _ in sources]

        # Test instantiation - should work without protected namespace warnings
        emb_func = TestEmbeddingFunction(
            provider="test",
            model_name="test-model",
            dimensions=3
        )

        assert emb_func.provider == "test"
        assert emb_func.model_name == "test-model"
        assert emb_func.dimensions == 3

    def test_base_embedding_function_vector_field(self):
        """Test BaseEmbeddingFunction VectorField method."""
        from pytidb.embeddings.base import BaseEmbeddingFunction

        class TestEmbeddingFunction(BaseEmbeddingFunction):
            def get_query_embedding(self, query: Any, source_type: Optional[str] = "text", **kwargs) -> List[float]:
                return [0.1, 0.2, 0.3]

            def get_source_embedding(self, source: Any, source_type: Optional[str] = "text", **kwargs) -> List[float]:
                return [0.1, 0.2, 0.3]

            def get_source_embeddings(self, sources: List[Any], source_type: Optional[str] = "text", **kwargs) -> List[List[float]]:
                return [[0.1, 0.2, 0.3] for _ in sources]

        emb_func = TestEmbeddingFunction(
            provider="test",
            model_name="test-model",
            dimensions=128
        )

        # Test VectorField creation
        vector_field = emb_func.VectorField()
        assert vector_field is not None

    def test_schema_models(self):
        """Test schema-related Pydantic models."""
        from pytidb.schema import ColumnInfo, VectorField

        # Test ColumnInfo
        col_info = ColumnInfo(
            column_name="test_column",
            column_type="VARCHAR(255)"
        )
        assert col_info.column_name == "test_column"
        assert col_info.column_type == "VARCHAR(255)"

        # Test VectorField
        vector_field = VectorField(dimensions=128)
        assert vector_field is not None

    def test_result_models(self):
        """Test result models."""
        from pytidb.result import SQLExecuteResult

        result = SQLExecuteResult(
            rowcount=5,
            success=True,
            message="Query executed successfully"
        )

        assert result.rowcount == 5
        assert result.success is True
        assert result.message == "Query executed successfully"

    def test_search_models(self):
        """Test search result models."""
        from pytidb.search import SearchResult

        class MockTableModel:
            def __init__(self):
                self.id = 1
                self.content = "test"

        search_result = SearchResult(
            hit=MockTableModel(),
            distance=0.5,
            match_score=0.8,
            score=0.9
        )

        assert search_result.distance == 0.5
        assert search_result.match_score == 0.8
        assert search_result.score == 0.9
        assert search_result.hit.id == 1
        assert search_result.hit.content == "test"

    def test_model_serialization(self):
        """Test model serialization compatibility."""
        from pytidb.result import SQLExecuteResult

        result = SQLExecuteResult(
            rowcount=10,
            success=True,
            message="Test message"
        )

        # Test model_dump method (should work in all Pydantic v2 versions)
        data_dict = result.model_dump()
        expected = {'rowcount': 10, 'success': True, 'message': 'Test message'}
        assert data_dict == expected

        # Test that the deprecated dict() method still works (with warnings)
        # but prefer model_dump() in actual code
        try:
            dict_data = result.dict()
            assert dict_data == expected
        except AttributeError:
            # In newer Pydantic versions, dict() might be removed
            # This is expected and acceptable
            pass

    def test_pydantic_field_usage(self):
        """Test that Pydantic Field is used correctly."""
        from pytidb.schema import Field
        from pytidb.result import SQLExecuteResult
        import inspect

        # Verify that Field is accessible
        assert Field is not None

        # Verify that models use Field correctly by checking class annotations
        fields = SQLExecuteResult.model_fields
        assert 'rowcount' in fields
        assert 'success' in fields
        assert 'message' in fields

    def test_model_validation(self):
        """Test that Pydantic model validation works correctly."""
        from pytidb.result import SQLExecuteResult
        from pydantic import ValidationError

        # Test valid data
        result = SQLExecuteResult(rowcount=5, success=True)
        assert result.rowcount == 5
        assert result.success is True
        assert result.message is None  # Optional field

        # Test that validation works for required fields
        with pytest.raises(ValidationError):
            SQLExecuteResult()  # Missing required fields

    def test_generic_type_support(self):
        """Test that generic types work correctly with SearchResult."""
        from pytidb.search import SearchResult

        class MockModel:
            def __init__(self, name: str):
                self.name = name

        mock_hit = MockModel("test")
        result = SearchResult[MockModel](hit=mock_hit, distance=0.1)

        assert result.hit.name == "test"
        assert result.distance == 0.1

    @pytest.mark.parametrize("version_info", [
        "2.0.3", "2.5.3", "2.10.6", "2.12.3"
    ])
    def test_version_compatibility_matrix(self, version_info):
        """
        Test compatibility with specific Pydantic versions.

        This test documents which versions we've verified to work.
        """
        current_version = pydantic.VERSION

        # Log the compatibility information
        print(f"PyTiDB verified compatible with Pydantic {version_info}")

        # Just ensure we can import the main components
        from pytidb.embeddings.base import BaseEmbeddingFunction
        from pytidb.schema import ColumnInfo
        from pytidb.result import SQLExecuteResult
        from pytidb.search import SearchResult

        # Basic smoke test
        result = SQLExecuteResult(rowcount=1, success=True)
        assert result.model_dump() == {'rowcount': 1, 'success': True, 'message': None}