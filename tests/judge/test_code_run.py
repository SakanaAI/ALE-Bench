import pytest

import ale_bench
from ale_bench.code_language import CodeLanguage, JudgeVersion
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

    @pytest.mark.parametrize(
        ("code_language", "judge_version", "code"),
        [
            pytest.param(
                CodeLanguage.BASH,
                JudgeVersion.V202510,
                """
#!/usr/bin/env bash
echo ok
""".lstrip(),
                id="bash-v202510",
            ),
            pytest.param(
                CodeLanguage.CPP23,
                JudgeVersion.V202510,
                """
#include <iostream>

int main() {
    std::cout << "ok" << std::endl;
    return 0;
}
""".lstrip(),
                id="cpp23-v202510",
            ),
            pytest.param(
                CodeLanguage.CSHARP,
                JudgeVersion.V202510,
                """
using System;

public static class Program
{
    public static void Main()
    {
        Console.WriteLine("ok");
    }
}
""".lstrip(),
                id="csharp-v202510",
            ),
            pytest.param(
                CodeLanguage.FISH,
                JudgeVersion.V202510,
                """
#!/usr/bin/env fish
echo ok
""".lstrip(),
                id="fish-v202510",
            ),
            pytest.param(
                CodeLanguage.FORTRAN,
                JudgeVersion.V202510,
                """
program main
implicit none
write(*,'(A)') 'ok'
end program main
""".lstrip(),
                id="fortran-v202510",
            ),
            pytest.param(
                CodeLanguage.GO,
                JudgeVersion.V202510,
                """
package main

import "fmt"

func main() {
    fmt.Println("ok")
}
""".lstrip(),
                id="go-v202510",
            ),
            pytest.param(
                CodeLanguage.HASKELL,
                JudgeVersion.V202510,
                """
main :: IO ()
main = putStrLn "ok"
""".lstrip(),
                id="haskell-v202510",
            ),
            pytest.param(
                CodeLanguage.JAVASCRIPT,
                JudgeVersion.V202510,
                """
'use strict';
console.log('ok');
""".lstrip(),
                id="javascript-v202510",
            ),
            pytest.param(
                CodeLanguage.JULIA,
                JudgeVersion.V202510,
                """
println("ok")
""".lstrip(),
                id="julia-v202510",
            ),
            pytest.param(
                CodeLanguage.LEAN,
                JudgeVersion.V202510,
                """
def main : IO Unit := do
IO.println "ok"
""".lstrip(),
                id="lean-v202510",
            ),
            pytest.param(
                CodeLanguage.OCAML,
                JudgeVersion.V202510,
                """
let () =
print_endline "ok"
""".lstrip(),
                id="ocaml-v202510",
            ),
            pytest.param(
                CodeLanguage.PERL,
                JudgeVersion.V202510,
                """
#!/usr/bin/env perl
use strict;
use warnings;
print "ok\\n";
""".lstrip(),
                id="perl-v202510",
            ),
            pytest.param(
                CodeLanguage.PYPY,
                JudgeVersion.V202510,
                """
print("ok")
""".lstrip(),
                id="pypy-v202510",
            ),
            pytest.param(
                CodeLanguage.PYTHON,
                JudgeVersion.V202510,
                """
print("ok")
""".lstrip(),
                id="python-v202510",
            ),
            pytest.param(
                CodeLanguage.RUST,
                JudgeVersion.V202510,
                """
fn main() {
    println!("ok");
}
""".lstrip(),
                id="rust-v202510",
            ),
            pytest.param(
                CodeLanguage.TYPESCRIPT,
                JudgeVersion.V202510,
                """
console.log("ok");
""".lstrip(),
                id="typescript-v202510",
            ),
        ],
    )
    def test_202510_smoke_all_languages(
        self,
        session: Session,
        code_language: CodeLanguage,
        judge_version: JudgeVersion,
        code: str,
    ) -> None:
        code_run_result = session.code_run(
            code=code,
            code_language=code_language,
            judge_version=judge_version,
            input_str="",
            time_limit=2.0,
        )
        assert code_run_result.stdin == ""
        assert code_run_result.stdout == "ok\n"
        assert code_run_result.stderr == ""
        assert code_run_result.exit_status == 0
        assert code_run_result.execution_time >= 0.0
        assert isinstance(code_run_result.memory_usage, int)
