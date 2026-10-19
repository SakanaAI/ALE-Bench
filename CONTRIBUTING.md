# Development and Contributing
- **Environment Setup:**
    ```sh
    git clone https://github.com/SakanaAI/ALE-Bench.git
    cd ALE-Bench
    uv sync --locked --all-extras
    ```

    This installs the default development dependency group and both optional extras (`eval` and `mcp`), matching CI. Run development commands from the repository root with `--all-extras` so both packages' dependencies are available. The core toolkit, evaluation package, and MCP server share the root `pyproject.toml`, `uv.lock`, and Git-tag-derived version; the MCP server lives in `src/ale_bench_mcp/`.

- **Docker Image Management:**
    ```sh
    # Build a base image (see scripts/docker_build_base_all.sh)
    # Specify --platform linux/amd64 if building on ARM for x86 compatibility
    docker build ./dockerfiles -t yimjk/ale-bench:python-202301-base -f ./dockerfiles/Dockerfile_python_202301_base

    # Push to Docker Hub (see scripts/docker_push_all.sh)
    docker image push yimjk/ale-bench:python-202301-base

    # Build a user-specific image with correct permissions (see scripts/docker_build_all.sh)
    docker build ./dockerfiles -t ale-bench:python-202301 -f ./dockerfiles/Dockerfile_python_202301 --build-arg UID=$(id -u) --build-arg GID=$(id -g)
    ```
    *Note: When pushing to Docker Hub, please change the image tag prefix `yimjk/` to your own username or organization name as appropriate (e.g., `your-username/ale-bench` or `your-organization/ale-bench`).*

- **Python Library Development:**
    ```sh
    # Linting
    uv run --locked --all-extras ruff check

    # Formatting
    uv run --locked --all-extras ruff format

    # Static Type Checking
    uv run --locked --all-extras ty check

    # Running Tests
    uv run --locked --all-extras pytest
    uv run --locked --all-extras pytest -m "not docker"  # Exclude tests requiring Docker

    # MCP client/configuration/storage tests only
    uv run --locked --all-extras pytest tests/mcp
    ```

    MCP client tests use a fake benchmark backend and exercise the server through the MCP SDK, including real stdio subprocesses. They do not require Docker, benchmark downloads, or LLM credentials. MCP tests skip if the MCP SDK is unavailable; use the setup above to include them. See the [MCP development guide](docs/mcp_server.md#development-versions-and-dependencies) for coverage and server configuration.

- **CI and Packaging:**
    The [Check workflow](.github/workflows/check.yml) runs lint, formatting, type checks, and tests with all extras enabled. The separate [Packaging workflow](.github/workflows/packaging.yml) builds the distribution and installs the wheel into clean environments for the base package, `[mcp]`, and `[eval]`.

    [The wheel smoke check](scripts/check_wheel_install.py) checks optional dependencies, missing-dependency guidance, MCP client communication, and the evaluation CLI's help output. It verifies imports come from the installed wheel and runs entry points outside the checkout. It does not run real Docker evaluations or call LLM APIs. The workflow invokes `.venv/bin/python` directly so project synchronization does not replace the installed wheel with checkout code.
