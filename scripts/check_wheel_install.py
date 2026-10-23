"""Check a clean wheel installation; set INSTALL_VARIANT to base, mcp, or eval."""

# ruff: noqa: INP001

import asyncio
import importlib
import importlib.metadata
import os
import subprocess
import sys
from pathlib import Path
from tempfile import TemporaryDirectory


def check_eval_install(variant: str, cwd: str) -> None:
    """Check eval imports and CLI help, or guidance when dependencies are absent."""
    if variant == "eval":
        for name in ("fire", "genai_prices", "numpy", "pandas", "psutil", "pydantic_ai", "ale_bench_eval"):
            package = importlib.import_module(name)
            if package.__file__ is None or "site-packages" not in Path(package.__file__).parts:
                msg = f"Package was not imported from the installed environment: {package.__file__}"
                raise RuntimeError(msg)

        result = subprocess.run(
            [sys.executable, "-m", "ale_bench_eval", "--", "--help"],
            cwd=cwd,
            capture_output=True,
            text=True,
            check=False,
            timeout=60,
        )
        if result.returncode != 0 or "MODEL_CONFIG_PATH" not in result.stdout + result.stderr:
            msg = f"Installed evaluation CLI failed to show help: {result}"
            raise RuntimeError(msg)
    else:
        for args in (
            [sys.executable, "-c", "import ale_bench_eval"],
            [sys.executable, "-m", "ale_bench_eval", "--", "--help"],
        ):
            result = subprocess.run(args, cwd=cwd, capture_output=True, text=True, check=False, timeout=60)  # noqa: S603
            if result.returncode != 1 or "install the `eval` extra requirements" not in result.stderr:
                msg = f"Missing evaluation installation instructions: {result}"
                raise RuntimeError(msg)


def main() -> None:
    """Verify optional dependencies and entry points outside the source tree."""
    variant = os.environ["INSTALL_VARIANT"]
    if variant not in {"base", "mcp", "eval"}:
        msg = f"Unknown installation variant: {variant}"
        raise ValueError(msg)
    installed = {dist.metadata["Name"].lower() for dist in importlib.metadata.distributions()}
    # Eval dependencies can bring in the SDK independently of the MCP extra.
    if variant != "eval" and ("mcp" in installed) != (variant == "mcp"):
        msg = f"Unexpected MCP SDK installation for {variant=}"
        raise RuntimeError(msg)
    for name in ("fire", "pydantic-ai"):
        if (name in installed) != (variant == "eval"):
            msg = f"Unexpected evaluation dependency installation: {name}, {variant=}"
            raise RuntimeError(msg)

    import ale_bench  # noqa: PLC0415

    if "mcp.server.mcpserver" in sys.modules:
        msg = "Importing ALE-Bench eagerly loaded the optional MCP server"
        raise RuntimeError(msg)

    packages = [ale_bench]
    if "mcp" in installed:
        import ale_bench_mcp  # noqa: PLC0415

        packages.append(ale_bench_mcp)
        if "ale_bench_mcp.server" in sys.modules:
            msg = "Importing the MCP package eagerly initialized the ALE-Bench server"
            raise RuntimeError(msg)

    # Verify that these are wheel installs, not imports from the checkout.
    for package in packages:
        if "site-packages" not in Path(package.__file__).parts:
            msg = f"Package was not imported from the installed wheel: {package.__file__}"
            raise RuntimeError(msg)

    command = str(Path(sys.executable).with_name("ale-bench-mcp"))
    with TemporaryDirectory() as cwd:
        check_eval_install(variant, cwd)
        if variant == "base":
            for args in (
                [sys.executable, "-c", "import ale_bench_mcp"],
                [command],
                [sys.executable, "-m", "ale_bench_mcp"],
            ):
                result = subprocess.run(args, cwd=cwd, capture_output=True, text=True, check=False, timeout=60)  # noqa: S603
                if (
                    result.returncode != 1
                    or "ImportError: Missing dependencies." not in result.stderr
                    or "pip install 'ale-bench[mcp]'" not in result.stderr
                ):
                    msg = f"Missing installation instructions: {result}"
                    raise RuntimeError(msg)
        elif variant == "mcp":
            from mcp import Client, StdioServerParameters  # noqa: PLC0415

            async def check_server() -> None:
                params = StdioServerParameters(command=command, cwd=cwd, env=dict(os.environ))
                async with Client(params, read_timeout_seconds=10) as client:
                    result = await client.call_tool("read_resource", {"uri": "ale://app"})
                    if result.is_error:
                        msg = f"Installed MCP server failed: {result}"
                        raise RuntimeError(msg)
                    await client.read_resource("ale://app")
                    tool_names = {tool.name for tool in (await client.list_tools()).tools}
                    expected = {
                        "start_session",
                        "close_session",
                        "generate_cases",
                        "evaluate",
                        "code_run",
                        "visualize_case",
                        "read_resource",
                    }
                    if tool_names != expected:
                        msg = f"Unexpected installed MCP tool set: {tool_names}"
                        raise RuntimeError(msg)

            asyncio.run(check_server())


if __name__ == "__main__":
    main()
