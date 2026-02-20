# Development and Contributing
- **Environment Setup:**
    ```sh
    git clone https://github.com/SakanaAI/ALE-Bench.git
    cd ALE-Bench
    uv sync --dev --extra eval
    ```

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
    uv run ruff check

    # Formatting
    uv run ruff format

    # Static Type Checking
    uv run ty check

    # Running Tests
    uv run pytest
    uv run pytest -m "not docker"  # Exclude tests requiring Docker
    ```
