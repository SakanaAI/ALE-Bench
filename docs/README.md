# ALE-Bench Documentation

## `Session` Object
The `Session` object is central to ALE-Bench, encapsulating the state and functionalities for an evaluation session on a specific problem. It facilitates input case generation, code execution, visualization, and evaluation.
Please refer to the [Session Object documentation](./session_object.md) for detailed information on how to use the `Session` object, including initialization, core methods, and parameters.

## `RatingCalculator` and `RankingCalculator`
ALE-Bench provides utilities for calculating ratings and rankings based on contest performance. For detailed information on how to use these calculators, including initialization and core methods, please refer to the [Rating and Ranking documentation](./rating_and_ranking.md).

## LLM Evaluation
ALE-Bench includes a comprehensive framework for evaluating Large Language Models (LLMs) for ALE-Bench (scripts: [ale_bench_eval](../src/ale_bench_eval/)). For setup and usage instructions, please refer to the [ALE-Bench Evaluation Tool documentation](./evaluation.md) for more details.

## Cloud Evaluation with AWS
ALE-Bench supports cloud-based evaluation using AWS. This allows you to run fair evaluations without needing to manage local resources. For setup and usage instructions, please refer to the [Cloud Evaluation documentation](./aws_evaluation.md).

## MCP Server
The MCP (Model Context Protocol) server is a lightweight HTTP server that provides a simple interface for interacting with the ALE-Bench toolkit. It allows you to run evaluations and manage sessions without needing to write Python code directly. For setup and usage instructions, please refer to the [MCP Server documentation](./mcp_server.md).
