from __future__ import annotations

import pytest

import ale_bench
from ale_bench.session import Session
from ale_bench.tool_wrappers.code_runner import ExitStatus


@pytest.mark.docker
class TestCodeRun:
    @pytest.fixture(scope="class")
    def session(self) -> Session:
        return ale_bench.start("ahc001", lite_version=False)

    def test_python(self, session: Session) -> None:
        code = "import sys\na, b = map(int, sys.stdin.read().split())\nprint(a + b)\n"
        code_run_result = session.code_run(code=code, code_language="python", input_str="2 3\n", time_limit=2.0)
        assert code_run_result.stdin == "2 3\n"
        assert code_run_result.stdout == "5"
        assert code_run_result.stderr == ""
        assert code_run_result.exit_status == 0
        assert code_run_result.execution_time >= 0.0
        assert isinstance(code_run_result.memory_usage, int)

    def test_python_stderr(self, session: Session) -> None:
        code = "import sys\nprint('hello')\nprint('error', file=sys.stderr)\n"
        code_run_result = session.code_run(code=code, code_language="python", input_str="", time_limit=2.0)
        assert code_run_result.stdin == ""
        assert code_run_result.stdout == "hello"
        assert code_run_result.stderr == "error"
        assert code_run_result.exit_status == 0
        assert code_run_result.execution_time >= 0.0
        assert isinstance(code_run_result.memory_usage, int)

    def test_python_nonzero_exit(self, session: Session) -> None:
        code = "import sys; sys.exit(3)\n"
        code_run_result = session.code_run(code=code, code_language="python", input_str="", time_limit=2.0)
        assert code_run_result.stdin == ""
        assert code_run_result.stdout == ""
        assert code_run_result.stderr == ""
        assert code_run_result.exit_status == 3
        assert code_run_result.execution_time >= 0.0
        assert isinstance(code_run_result.memory_usage, int)

    def test_python_tle(self, session: Session) -> None:
        code = "while True: pass\n"
        code_run_result = session.code_run(code=code, code_language="python", input_str="", time_limit=1.0)
        assert code_run_result.stdin == ""
        assert code_run_result.stdout == ""
        assert code_run_result.stderr == ""
        assert code_run_result.exit_status == ExitStatus.TIME_LIMIT_EXCEEDED.value
        assert code_run_result.execution_time >= 1.0
        assert isinstance(code_run_result.memory_usage, int)

    def test_python_mle(self, session: Session) -> None:
        code = "a = ' ' * (128 * 1024 * 1024)\n"
        code_run_result = session.code_run(
            code=code, code_language="python", input_str="", time_limit=2.0, memory_limit=64 * 1024 * 1024
        )
        assert code_run_result.stdin == ""
        assert code_run_result.stdout == ""
        assert code_run_result.stderr == ""
        assert code_run_result.exit_status == ExitStatus.MEMORY_LIMIT_EXCEEDED.value
        assert code_run_result.execution_time >= 0.0
        assert isinstance(code_run_result.memory_usage, int)
