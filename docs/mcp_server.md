# MCP (Model Context Protocol) Server
The MCP server is a lightweight HTTP server that provides a simple interface for interacting with the ALE-Bench toolkit. It allows you to run evaluations and manage sessions without needing to write Python code directly.

## Setup
1. Install Node.js and npm
    ```sh
    # Install nvm (Node Version Manager) for easy Node.js management
    curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.40.3/install.sh | bash
    export NVM_DIR="$HOME/.nvm"
    [ -s "$NVM_DIR/nvm.sh" ] && \. "$NVM_DIR/nvm.sh"  # This loads nvm
    [ -s "$NVM_DIR/bash_completion" ] && \. "$NVM_DIR/bash_completion"  # This loads nvm bash_completion
    # Install the latest LTS version of Node.js
    nvm install --lts
    # Install the Model Context Protocol Inspector
    npm install -g @modelcontextprotocol/inspector
    ```
2. Install the MCP server dependencies using pip or uv:
    ```sh
    cd mcp
    uv sync
    uv sync --extra dev  # For development dependencies
    ```

## Running the MCP Server
```sh
# Ensure you are in the mcp directory (e.g., cd mcp from the project root)
uv run mcp run server.py
uv run mcp dev server.py --with-editable .  # For development
```

## Use with Claude Desktop
1. Open the `claude_desktop_config.json` file that configures the Claude Desktop. Add the following configuration to connect to the MCP server, ensuring you replace `/path/to/ALE-Bench` in the `args` with the actual absolute path to your cloned `ALE-Bench` repository directory:
    ```json
    {
        "mcpServers": {
            "ALE-Bench MCP Server": {
                "command": "/bin/bash",
                "args": [
                    "-c",
                    "cd /path/to/ALE-Bench/mcp && uv run --with ale_bench --with mcp[cli] mcp run /path/to/ALE-Bench/mcp/server.py"
                ]
            }
        }
    }
    ```
2. Restart the Claude Desktop application to apply the changes.

<img width="680" alt="MCP_Claude_Desktop" src="https://github.com/user-attachments/assets/d9f22719-5686-406d-aa94-44406c700d6f" />

## Available Tools
The MCP server provides tools that wrap the core functionalities of the `Session` object. You can use these tools to perform actions like:
- **Session Management:** `start_session`, `close_session`, `list_current_sessions`
- **Problem Information:** `list_problem_ids`, `get_problem`, `get_public_seeds`
- **Evaluation:** `public_eval`, `private_eval`, `case_eval`, `case_gen_eval`
- **Visualization:** `case_vis`, `case_gen_vis`

For detailed information on the parameters and behavior of these functions, please refer to the [Session Object documentation](./session_object.md) or the [server implementation](../mcp/server.py).
