# Import all MySQL types from SQLAlchemy MySQL dialect
from sqlalchemy.dialects.mysql import (
    # Numeric types
    BIGINT,
    BIT,
    DECIMAL,
    DOUBLE,
    FLOAT,
    INTEGER,
    MEDIUMINT,
    NUMERIC,
    REAL,
    SMALLINT,
    TINYINT,
    # String types
    CHAR,
    ENUM,
    LONGTEXT,
    MEDIUMTEXT,
    NCHAR,
    NVARCHAR,
    SET,
    TEXT,
    TINYTEXT,
    VARCHAR,
    # Binary types
    BINARY,
    BLOB,
    LONGBLOB,
    MEDIUMBLOB,
    TINYBLOB,
    VARBINARY,
    # Date and time types
    DATE,
    DATETIME,
    TIME,
    TIMESTAMP,
    YEAR,
    # JSON type
    JSON,
    # Boolean type
    BOOLEAN,
)


# Import TiDB-specific VECTOR type
from pytidb.orm.vector import VECTOR

# Common aliases for convenience
INT = INTEGER  # INT is an alias for INTEGER

# Re-export all types for easy import
__all__ = [
    # Numeric types
    "BIGINT",
    "BIT",
    "DECIMAL",
    "DOUBLE",
    "FLOAT",
    "INTEGER",
    "INT",  # alias for INTEGER
    "MEDIUMINT",
    "NUMERIC",
    "REAL",
    "SMALLINT",
    "TINYINT",
    # String types
    "CHAR",
    "ENUM",
    "LONGTEXT",
    "MEDIUMTEXT",
    "NCHAR",
    "NVARCHAR",
    "SET",
    "TEXT",
    "TINYTEXT",
    "VARCHAR",
    # Binary types
    "BINARY",
    "BLOB",
    "LONGBLOB",
    "MEDIUMBLOB",
    "TINYBLOB",
    "VARBINARY",
    # Date and time types
    "DATE",
    "DATETIME",
    "TIME",
    "TIMESTAMP",
    "YEAR",
    # JSON type
    "JSON",
    # Boolean type
    "BOOLEAN",
    # TiDB-specific types
    "VECTOR",
]
