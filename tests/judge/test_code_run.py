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

    def test_cpp20(self, session: Session) -> None:
        code = """#include <iostream>
int main() {
    int a, b;
    std::cin >> a >> b;
    std::cout << (a + b) << '\\n';
    return 0;
}
"""
        code_run_result = session.code_run(code=code, code_language="cpp20", input_str="2 3\n", time_limit=2.0)
        assert code_run_result.stdin == "2 3\n"
        assert code_run_result.stdout == "5\n"
        assert code_run_result.stderr == ""
        assert code_run_result.exit_status == 0
        assert code_run_result.execution_time >= 0.0
        assert isinstance(code_run_result.memory_usage, int)

    def test_cpp20_stderr(self, session: Session) -> None:
        code = """#include <iostream>
int main() {
    std::cout << \"hello\" << '\\n';
    std::cerr << \"error\" << std::endl;
    return 0;
}
"""
        code_run_result = session.code_run(code=code, code_language="cpp20", input_str="", time_limit=2.0)
        assert code_run_result.stdin == ""
        assert code_run_result.stdout == "hello\n"
        assert code_run_result.stderr == "error"  # NOTE: the standard error string is stripped
        assert code_run_result.exit_status == 0
        assert code_run_result.execution_time >= 0.0
        assert isinstance(code_run_result.memory_usage, int)

    def test_cpp20_nonzero_exit(self, session: Session) -> None:
        exit_status = 3
        code = f"#include <cstdlib>\nint main() {{ std::exit({exit_status}); }}\n"
        code_run_result = session.code_run(code=code, code_language="cpp20", input_str="", time_limit=2.0)
        assert code_run_result.stdin == ""
        assert code_run_result.stdout == ""
        assert code_run_result.stderr == ""
        assert code_run_result.exit_status == exit_status
        assert code_run_result.execution_time >= 0.0
        assert isinstance(code_run_result.memory_usage, int)

    def test_cpp20_tle(self, session: Session) -> None:
        code = "int main() { while (true); }\n"
        code_run_result = session.code_run(code=code, code_language="cpp20", input_str="", time_limit=1.0)
        assert code_run_result.stdin == ""
        assert code_run_result.stdout == ""
        assert code_run_result.stderr == ""
        assert code_run_result.exit_status == ExitStatus.TIME_LIMIT_EXCEEDED.value
        assert code_run_result.execution_time >= 1.0
        assert isinstance(code_run_result.memory_usage, int)

    def test_cpp20_mle(self, session: Session) -> None:
        code = "#include <vector>\nint main() { std::vector<int> a(128 * 1024 * 1024); }\n"
        code_run_result = session.code_run(
            code=code, code_language="cpp20", input_str="", time_limit=2.0, memory_limit=64 * 1024 * 1024
        )
        assert code_run_result.stdin == ""
        assert code_run_result.stdout == ""
        assert code_run_result.stderr == ""
        assert code_run_result.exit_status == ExitStatus.MEMORY_LIMIT_EXCEEDED.value
        assert code_run_result.execution_time >= 0.0
        assert isinstance(code_run_result.memory_usage, int)

    def test_python(self, session: Session) -> None:
        code = "import sys\na, b = map(int, sys.stdin.read().split())\nprint(a + b)\n"
        code_run_result = session.code_run(code=code, code_language="python", input_str="2 3\n", time_limit=2.0)
        assert code_run_result.stdin == "2 3\n"
        assert code_run_result.stdout == "5\n"
        assert code_run_result.stderr == ""
        assert code_run_result.exit_status == 0
        assert code_run_result.execution_time >= 0.0
        assert isinstance(code_run_result.memory_usage, int)

    def test_python_stderr(self, session: Session) -> None:
        code = "import sys\nprint('hello')\nprint('error', file=sys.stderr)\n"
        code_run_result = session.code_run(code=code, code_language="python", input_str="", time_limit=2.0)
        assert code_run_result.stdin == ""
        assert code_run_result.stdout == "hello\n"
        assert code_run_result.stderr == "error"  # NOTE: the standard error string is stripped
        assert code_run_result.exit_status == 0
        assert code_run_result.execution_time >= 0.0
        assert isinstance(code_run_result.memory_usage, int)

    def test_python_nonzero_exit(self, session: Session) -> None:
        exit_status = 3
        code = f"import sys; sys.exit({exit_status})\n"
        code_run_result = session.code_run(code=code, code_language="python", input_str="", time_limit=2.0)
        assert code_run_result.stdin == ""
        assert code_run_result.stdout == ""
        assert code_run_result.stderr == ""
        assert code_run_result.exit_status == exit_status
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

    def test_rust(self, session: Session) -> None:
        code = """use std::io::{self, Read};
fn main() {
    let mut input = String::new();
    io::stdin().read_to_string(&mut input).unwrap();
    let mut nums = input.split_whitespace().map(|x| x.parse::<i32>().unwrap());
    let a = nums.next().unwrap();
    let b = nums.next().unwrap();
    println!("{}", a + b);
}
"""
        code_run_result = session.code_run(code=code, code_language="rust", input_str="2 3\n", time_limit=2.0)
        assert code_run_result.stdin == "2 3\n"
        assert code_run_result.stdout == "5\n"
        assert code_run_result.stderr == ""
        assert code_run_result.exit_status == 0
        assert code_run_result.execution_time >= 0.0
        assert isinstance(code_run_result.memory_usage, int)

    def test_rust_stderr(self, session: Session) -> None:
        code = """use std::io::{self, Write};
fn main() {
    println!(\"hello\");
    let mut stderr = io::stderr();
    writeln!(stderr, \"error\").unwrap();
}
"""
        code_run_result = session.code_run(code=code, code_language="rust", input_str="", time_limit=2.0)
        assert code_run_result.stdin == ""
        assert code_run_result.stdout == "hello\n"
        assert code_run_result.stderr == "error"  # NOTE: the standard error string is stripped
        assert code_run_result.exit_status == 0
        assert code_run_result.execution_time >= 0.0
        assert isinstance(code_run_result.memory_usage, int)

    def test_rust_nonzero_exit(self, session: Session) -> None:
        exit_status = 3
        code = f"""fn main() {{ std::process::exit({exit_status}); }}\n"""
        code_run_result = session.code_run(code=code, code_language="rust", input_str="", time_limit=2.0)
        assert code_run_result.stdin == ""
        assert code_run_result.stdout == ""
        assert code_run_result.stderr == ""
        assert code_run_result.exit_status == exit_status
        assert code_run_result.execution_time >= 0.0
        assert isinstance(code_run_result.memory_usage, int)

    def test_rust_tle(self, session: Session) -> None:
        code = "fn main() { loop {} }\n"
        code_run_result = session.code_run(code=code, code_language="rust", input_str="", time_limit=1.0)
        assert code_run_result.stdin == ""
        assert code_run_result.stdout == ""
        assert code_run_result.stderr == ""
        assert code_run_result.exit_status == ExitStatus.TIME_LIMIT_EXCEEDED.value
        assert code_run_result.execution_time >= 1.0
        assert isinstance(code_run_result.memory_usage, int)

    def test_rust_mle(self, session: Session) -> None:
        code = """fn main() {
    let mut arr: Vec<u64> = vec![0; 1024 * 1024];
    for i in 1..16 {
        let mut page = vec![i as u64; 1024 * 1024];
        arr.extend(page);
    }
}
"""
        code_run_result = session.code_run(
            code=code, code_language="rust", input_str="", time_limit=2.0, memory_limit=64 * 1024 * 1024
        )
        assert code_run_result.stdin == ""
        assert code_run_result.stdout == ""
        assert code_run_result.stderr == ""
        assert code_run_result.exit_status == ExitStatus.MEMORY_LIMIT_EXCEEDED.value
        assert code_run_result.execution_time >= 0.0
        assert isinstance(code_run_result.memory_usage, int)
