from typing import Optional, Union, List
import numpy as np
import sqlalchemy
from sqlalchemy.dialects.mysql.base import ischema_names

# TiDB Vector has a limitation on the dimension length
MAX_DIM = 16000
MIN_DIM = 1

# Define the vector data type
VectorDataType = Union[np.ndarray, List[float]]


class VECTOR(sqlalchemy.types.UserDefinedType):
    """
    Represents a vector column type in TiDB.
    """

    dim: Optional[int]

    cache_ok = True

    def __init__(self, dim: Optional[int] = None):
        if dim is not None and not isinstance(dim, int):
            raise ValueError("expected dimension to be an integer or None")

        # tidb vector dimention length has limitation
        if dim is not None and (dim < MIN_DIM or dim > MAX_DIM):
            raise ValueError(f"expected dimension to be in [{MIN_DIM}, {MAX_DIM}]")

        super().__init__()
        self.dim = dim

    def get_col_spec(self, **kw):
        """
        Returns the column specification for the vector column.

        If the dimension is not specified, it returns "VECTOR".
        Otherwise, it returns "VECTOR(<dimension>)".

        :param kw: Additional keyword arguments.
        :return: The column specification string.
        """

        if self.dim is None:
            return "VECTOR"
        return f"VECTOR({self.dim})"

    def bind_processor(self, dialect):
        """Convert the vector float array to a string representation suitable for binding to a database column."""

        def process(value):
            return encode_vector(value, self.dim)

        return process

    def result_processor(self, dialect, coltype):
        """Convert the vector data from the database into vector array."""

        def process(value):
            return decode_vector(value)

        return process

    class comparator_factory(sqlalchemy.types.UserDefinedType.Comparator):
        """Returns a comparator factory that provides the distance functions."""

        def l1_distance(self, other: VectorDataType):
            formatted_other = encode_vector(other, self.type.dim)
            return sqlalchemy.func.VEC_L1_DISTANCE(self, formatted_other).label(
                "l1_distance"
            )

        def l2_distance(self, other: VectorDataType):
            formatted_other = encode_vector(other, self.type.dim)
            return sqlalchemy.func.VEC_L2_DISTANCE(self, formatted_other).label(
                "l2_distance"
            )

        def cosine_distance(self, other: VectorDataType):
            formatted_other = encode_vector(other, self.type.dim)
            return sqlalchemy.func.VEC_COSINE_DISTANCE(self, formatted_other).label(
                "cosine_distance"
            )

        def negative_inner_product(self, other: VectorDataType):
            formatted_other = encode_vector(other, self.type.dim)
            return sqlalchemy.func.VEC_NEGATIVE_INNER_PRODUCT(
                self, formatted_other
            ).label("negative_inner_product")

        def embed_l1_distance(self, query: str):
            return sqlalchemy.func.VEC_EMBED_L1_DISTANCE(self, query).label(
                "embed_l1_distance"
            )

        def embed_l2_distance(self, query: str):
            return sqlalchemy.func.VEC_EMBED_L2_DISTANCE(self, query).label(
                "embed_l2_distance"
            )

        def embed_cosine_distance(self, query: str):
            return sqlalchemy.func.VEC_EMBED_COSINE_DISTANCE(self, query).label(
                "embed_cosine_distance"
            )

        def embed_negative_inner_product(self, query: str):
            return sqlalchemy.func.VEC_EMBED_NEGATIVE_INNER_PRODUCT(self, query).label(
                "embed_negative_inner_product"
            )


# For reflection, make mysql dialect aware of VECTOR type.
ischema_names["vector"] = VECTOR


def encode_vector(value: VectorDataType, dim=None):
    if value is None:
        return value

    if dim is not None and len(value) != dim:
        raise ValueError(f"expected {dim} dimensions, but got {len(value)}")

    if isinstance(value, np.ndarray):
        if value.ndim != 1:
            raise ValueError("expected ndim to be 1")
        return f"[{','.join(map(str, value))}]"

    return str(value)


def decode_vector(value: str) -> np.ndarray:
    if value is None:
        return value

    if value == "[]":
        return np.array([], dtype=np.float32)

    return np.array(value[1:-1].split(","), dtype=np.float32)
