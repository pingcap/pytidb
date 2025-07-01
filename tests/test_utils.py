from datetime import datetime
from typing import Optional, Any
import pytest
from sqlalchemy import BigInteger

from pytidb import TiDBClient
from pytidb.embeddings import EmbeddingFunction
from pytidb.schema import TableModel, Field, Column
from pytidb.datatype import Vector
from pytidb.utils import build_tidb_dsn, check_vector_column


def test_build_tidb_dsn():
    # For TiDB Serverless
    dsn = build_tidb_dsn(
        host="gateway01.us-west-2.prod.aws.tidbcloud.com",
        username="xxxxxxxx.root",
        password="$password$",
    )
    assert dsn.host == "gateway01.us-west-2.prod.aws.tidbcloud.com"
    assert dsn.port == 4000
    assert dsn.username == "xxxxxxxx.root"
    assert dsn.password == "%24password%24"
    assert dsn.path == "/test"
    assert dsn.query == "ssl_verify_cert=true&ssl_verify_identity=true"
    assert (
        str(dsn)
        == "mysql+pymysql://xxxxxxxx.root:%24password%24@gateway01.us-west-2.prod.aws.tidbcloud.com:4000/test?ssl_verify_cert=true&ssl_verify_identity=true"
    )

    # For TiDB Cluster on local.
    dsn = build_tidb_dsn(host="localhost", username="root", password="password")
    assert dsn.host == "localhost"
    assert dsn.port == 4000
    assert dsn.username == "root"
    assert dsn.password == "password"
    assert dsn.path == "/test"
    assert dsn.query is None
    assert str(dsn) == "mysql+pymysql://root:password@localhost:4000/test"


@pytest.fixture(scope="module")
def issue_table(client: TiDBClient):
    """Create an Issue table with multiple vector columns for testing."""
    ISSUE_TABLE_NAME = "test_issue_utils"
    
    text_embedding_function = EmbeddingFunction("openai/text-embedding-3-small")
    
    class Issue(TableModel, table=True):
        """
        Issue model that mirrors GitHub's Issue structure.
        Based on PyGithub's Issue class and GitHub REST API.
        """
        __tablename__ = ISSUE_TABLE_NAME
        
        # GitHub Issue identifiers - using BIGINT for large GitHub IDs
        github_issue_id: int = Field(sa_column=Column(BigInteger, primary_key=True))
        github_issue_number: int = Field(index=True)  # Issue number in the repository
        node_id: str  # GitHub's node ID for GraphQL API
        
        # Repository information
        repository_name: str = Field(index=True)  # Repository name (e.g., "owner/repo")
        repository_owner: str = Field(index=True)  # Repository owner
        repository_id: int  # GitHub repository ID
        
        # Issue content
        title: str  # Issue title
        body: Optional[str] = None  # Issue body/description (can be None)
        
        # Issue status
        state: str = Field(index=True)  # Issue state (open/closed)
        state_reason: Optional[str] = None  # Reason for state change
        locked: bool = Field(default=False)  # Whether the issue is locked
        active_lock_reason: Optional[str] = None  # Reason for locking
        
        # User information (minimal)
        author_login: str = Field(index=True)  # Issue author GitHub login
        author_id: int  # Issue author GitHub ID
        closed_by_login: Optional[str] = None  # Who closed the issue
        closed_by_id: Optional[int] = None  # ID of who closed the issue
        
        # Assignees and labels (JSON storage)
        assignees: Optional[str] = None  # JSON string of assignee data
        labels: Optional[str] = None  # JSON string of label data
        
        # Milestone
        milestone_title: Optional[str] = None
        milestone_id: Optional[int] = None
        
        # Timestamps
        created_at: datetime
        updated_at: datetime
        closed_at: Optional[datetime] = None
        
        # URLs
        html_url: str  # GitHub issue URL
        url: str  # API URL
        
        # Vector embeddings for content search
        title_vec: Optional[Any] = text_embedding_function.VectorField(
            source_field="title",
        )
        body_vec: Optional[Any] = text_embedding_function.VectorField(
            source_field="body",
        )
        
        # Additional vector column with explicit Vector type
        manual_vec: Optional[Any] = Field(sa_column=Column(Vector(512)))

    tbl = client.create_table(schema=Issue, mode="overwrite")
    return tbl


def test_check_vector_column_valid_columns(issue_table):
    """Test check_vector_column with valid vector columns."""
    columns = issue_table._columns
    
    # Test title_vec (from VectorField)
    result = check_vector_column(columns, "title_vec")
    assert result is not None
    assert result.name == "title_vec"
    
    # Test body_vec (from VectorField)
    result = check_vector_column(columns, "body_vec")
    assert result is not None
    assert result.name == "body_vec"
    
    # Test manual_vec (explicit Vector type)
    result = check_vector_column(columns, "manual_vec")
    assert result is not None
    assert result.name == "manual_vec"


def test_check_vector_column_nonexistent_column(issue_table):
    """Test check_vector_column with non-existent column."""
    columns = issue_table._columns
    
    with pytest.raises(ValueError, match="Non-exists vector column: nonexistent_column"):
        check_vector_column(columns, "nonexistent_column")


def test_check_vector_column_non_vector_column(issue_table):
    """Test check_vector_column with non-vector columns."""
    columns = issue_table._columns
    
    # Test with string column
    with pytest.raises(ValueError, match="Invalid vector column"):
        check_vector_column(columns, "title")
    
    # Test with integer column
    with pytest.raises(ValueError, match="Invalid vector column"):
        check_vector_column(columns, "github_issue_id")
    
    # Test with boolean column
    with pytest.raises(ValueError, match="Invalid vector column"):
        check_vector_column(columns, "locked")


def test_check_vector_column_edge_cases():
    """Test check_vector_column with edge cases."""
    # Test with empty columns dict
    empty_columns = {}
    with pytest.raises(ValueError, match="Non-exists vector column: any_column"):
        check_vector_column(empty_columns, "any_column")
    
    # Test with None column name
    columns = {"test": None}
    with pytest.raises(ValueError, match="Non-exists vector column: None"):
        check_vector_column(columns, None)
