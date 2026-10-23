"""Run the ALE-Bench MCP server with ``python -m ale_bench_mcp``."""

from ale_bench_mcp.server import mcp


def main() -> None:
    """Run the MCP server over stdio; package initialization checks dependencies."""
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
