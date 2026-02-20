"""ALE-Bench evaluation package."""

import importlib
import importlib.metadata

try:
    for package_name in ("fire", "genai_prices", "numpy", "pandas", "psutil", "pydantic_ai"):
        importlib.import_module(package_name)
except ImportError as e:
    msg = "Missing dependencies. Please install the `eval` extra requirements."
    raise ImportError(msg) from e

try:
    __version__ = importlib.metadata.version("ale_bench")
except importlib.metadata.PackageNotFoundError:
    __version__ = "0.0.0"  # Fallback version if package is not installed
