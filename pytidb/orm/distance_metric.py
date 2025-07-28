import enum
from typing import Union


class DistanceMetric(str, enum.Enum):
    """
    An enumeration representing different types of distance metrics.

    - `DistanceMetric.L1`: L1 (Manhattan) distance metric.
    - `DistanceMetric.L2`: L2 (Euclidean) distance metric.
    - `DistanceMetric.COSINE`: Cosine distance metric.
    - `DistanceMetric.NEGATIVE_INNER_PRODUCT`: Negative inner product distance metric.
    """

    L1 = "L1"
    L2 = "L2"
    COSINE = "COSINE"
    NEGATIVE_INNER_PRODUCT = "NEGATIVE_INNER_PRODUCT"

    def to_sql_func(self):
        """
        Converts the DistanceMetric to its corresponding SQL function name.

        Returns:
            str: The SQL function name.

        Raises:
            ValueError: If the DistanceMetric enum member is not supported.
        """
        if self == DistanceMetric.L1:
            return "VEC_L1_DISTANCE"
        elif self == DistanceMetric.L2:
            return "VEC_L2_DISTANCE"
        elif self == DistanceMetric.COSINE:
            return "VEC_COSINE_DISTANCE"
        elif self == DistanceMetric.NEGATIVE_INNER_PRODUCT:
            return "VEC_NEGATIVE_INNER_PRODUCT"
        else:
            raise ValueError(
                f"Distance metric {self} has no corresponding SQL function"
            )


def validate_distance_metric(value: Union[str, DistanceMetric]) -> DistanceMetric:
    """
    Validate and convert distance metric parameter.

    Args:
        value: String or DistanceMetric enum to validate and convert

    Returns:
        DistanceMetric: The validated and converted enum value

    Raises:
        ValueError: If the value is not a valid distance metric

    Examples:
        >>> validate_distance_metric("COSINE")
        DistanceMetric.COSINE
        >>> validate_distance_metric("l2")
        DistanceMetric.L2
        >>> validate_distance_metric(DistanceMetric.COSINE)
        DistanceMetric.COSINE
    """
    if isinstance(value, DistanceMetric):
        return value
    elif isinstance(value, str):
        value_upper = value.upper()
        if value_upper == "L1":
            return DistanceMetric.L1
        elif value_upper == "L2":
            return DistanceMetric.L2
        elif value_upper == "COSINE":
            return DistanceMetric.COSINE
        elif value_upper == "NEGATIVE_INNER_PRODUCT":
            return DistanceMetric.NEGATIVE_INNER_PRODUCT
        else:
            raise ValueError(
                f"Invalid distance metric: {value}. Valid options: L1, L2, COSINE, NEGATIVE_INNER_PRODUCT"
            )
    else:
        raise ValueError(
            f"Invalid distance metric type: {type(value)}. Expected string or DistanceMetric enum"
        )
