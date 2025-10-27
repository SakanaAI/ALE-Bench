from __future__ import annotations

from typing import Sequence

from PIL import Image
from pydantic import Field
from pydantic.functional_serializers import PlainSerializer
from pydantic.functional_validators import BeforeValidator
from pydantic.json_schema import WithJsonSchema
from typing_extensions import Annotated

from ale_bench.data import Problem
from ale_bench.result import CaseResult, Result
from ale_bench.utils import base64_to_pil, pil_to_base64

SerializableImage = Annotated[
    Image.Image,
    # Deserialize from base64 string
    BeforeValidator(lambda v: base64_to_pil(v) if isinstance(v, str) else v),
    # Serialize to base64 string
    PlainSerializer(lambda img: pil_to_base64(img), return_type=str),  # NOTE: when_used="json" may be helpful
    # JSON Schema representation
    WithJsonSchema(
        {
            "type": "string",
            "format": "byte",
            "contentEncoding": "base64",
            "contentMediaType": "image/*",
            "description": "Base64-encoded image data (png/jpeg/webp)",
        }
    ),
]


class ProblemSerializable(Problem):
    """Serializable version of Problem for JSON serialization.

    This class extends Problem to include serialization and deserialization of the `statement_images` field.
    This class is especially useful for hosting APIs that need to serialize images in a format suitable for JSON.
    """

    statement_images: dict[str, SerializableImage | list[SerializableImage]] = Field(
        description="Problem statement images in PIL Image format (key: image name, value: image object)",
        default_factory=dict,
    )

    @classmethod
    def from_problem(cls, problem: Problem) -> "ProblemSerializable":
        """Create a ProblemSerializable from an existing Problem."""
        return cls.model_validate(problem.model_dump())


class CaseResultSerializable(CaseResult):
    """Serializable version of CaseResult for JSON serialization.

    This class extends CaseResult to include serialization and deserialization of the `local_visualization` field.
    This class is especially useful for hosting APIs that need to serialize images in a format suitable for JSON.
    """

    local_visualization: SerializableImage | None = Field(default=None, description="The final state of the submission")

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
