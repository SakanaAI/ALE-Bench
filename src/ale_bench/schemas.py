from __future__ import annotations

from typing import Sequence

from PIL import Image
from pydantic import Field, field_serializer, field_validator

from ale_bench.result import CaseResult, Result
from ale_bench.utils import base64_to_pil, pil_to_base64


class CaseResultSerializable(CaseResult):
    """Serializable version of CaseResult for JSON serialization.

    This class extends CaseResult to include serialization and deserialization of the `local_visualization` field.
    This class is especially useful for hosting APIs that need to serialize images in a format suitable for JSON.
    """

    @field_serializer("local_visualization")
    def serialize_local_visualization(self, value: Image.Image | None) -> str | None:
        """Serialize the local visualization image to a base64 string."""
        if value is None:
            return None
        return pil_to_base64(value)

    @field_validator("local_visualization", mode="before")
    def deserialize_local_visualization(cls, value: Image.Image | str | None) -> Image.Image | None:
        """Deserialize the local visualization from a base64 string to an Image."""
        if isinstance(value, str):
            try:
                return base64_to_pil(value)
            except Exception as e:
                raise ValueError(f"Invalid base64 image data: {e}")
        elif isinstance(value, Image.Image):
            return value
        return None

    @classmethod
    def from_case_result(cls, case_result: CaseResult) -> "CaseResultSerializable":
        """Create a CaseResultSerializable from an existing CaseResult."""
        return cls.model_validate(case_result.model_dump())


class ResultSerializable(Result):
    """Serializable version of Result for JSON serialization.

    This class extends Result to include serialization of the `case_results` field.
    This is useful for APIs that need to return results in a JSON format.
    """

    case_results: Sequence[CaseResultSerializable] = Field(description="The results of each case")

    @classmethod
    def from_result(cls, result: Result) -> "ResultSerializable":
        """Create a ResultSerializable from an existing Result."""
        return cls.model_validate(result.model_dump())
