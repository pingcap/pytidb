from sqlalchemy.engine.result import SimpleResultMetaData
from sqlalchemy.engine.row import Row


def create_row_from_dict(data: dict) -> Row:
    """Create a Row object from a dictionary.

    Args:
        data: A dictionary containing the row data

    Returns:
        A Row object with the data from the dictionary
    """
    # Create metadata with column names from dict keys
    metadata = SimpleResultMetaData(tuple(data.keys()))

    # Create Row object with metadata and values
    row = Row(
        metadata,
        None,  # processors
        metadata._key_to_index,
        tuple(data.values()),
    )

    return row


def create_rows_from_list(data: list[dict]) -> list[Row]:
    """Create a list of Row objects from a list of dictionaries.

    Args:
        data: A list of dictionaries containing the row data

    Returns:
        A list of Row objects with the data from the dictionaries
    """
    return [create_row_from_dict(row) for row in data]
