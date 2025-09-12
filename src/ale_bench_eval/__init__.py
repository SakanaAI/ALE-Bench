"""ALE-Bench evaluation package."""

import importlib.metadata
import sys

if sys.version_info < (3, 10):
    raise RuntimeError("ALE-Bench evaluation requires Python 3.10 or higher.")

try:
    import fire  # noqa: F401
    import genai_prices  # noqa: F401
    import numpy  # noqa: F401
    import pandas  # noqa: F401
    import psutil  # noqa: F401
    import pydantic_ai  # noqa: F401
except ImportError as e:
    raise ImportError("Missing dependencies. Please install the `eval` extra requirements.") from e

try:
    __version__ = importlib.metadata.version("ale_bench")
except importlib.metadata.PackageNotFoundError:
    __version__ = "0.0.0"  # Fallback version if package is not installed
