"""Judge-version/language command profiles."""

from __future__ import annotations

from dataclasses import dataclass
from textwrap import dedent


@dataclass(frozen=True)
class JudgeLanguageProfile:
    """Compile/run and file-path settings for one language profile."""

    compile_command: str
    run_command: str
    submission_file_path: str
    object_file_path: str


CPP23_202510_COMPILE_COMMAND = dedent(
    """
    export PATH=/opt/gcc-15.2.0/bin:$PATH
    export LD_LIBRARY_PATH=/opt/gcc-15.2.0/lib64:/opt/gcc-15.2.0/lib:${LD_LIBRARY_PATH:-}
    USER_BUILD_FLAGS=(
    "-DATCODER"
    "-DNOMINMAX"
    "-DONLINE_JUDGE"
    "-DOR_PROTO_DLL="
    "-DPROTOBUF_USE_DLLS"
    "-DUSE_BOP"
    "-DUSE_CBC"
    "-DUSE_CLP"
    "-DUSE_GLOP"
    "-DUSE_LP_PARSER"
    "-DUSE_MATH_OPT"
    "-DUSE_PDLP"
    "-DUSE_SCIP"
    "-I/opt/gcc-15.2.0/include"
    "-I/opt/gcc-15.2.0/include/torch/csrc/api/include"
    "-O2"
    "-Wall"
    "-Wextra"
    "-fconstexpr-depth=1024"
    "-fconstexpr-loop-limit=524288"
    "-fconstexpr-ops-limit=2097152"
    "-flto=auto"
    "-fmodules"
    "-ftrivial-auto-var-init=zero"
    "-march=native"
    "-pthread"
    "-std=gnu++23"
    "-Wl,--as-needed"
    "-L/opt/gcc-15.2.0/lib64"
    "-Wl,-R/opt/gcc-15.2.0/lib64"
    "-L/opt/gcc-15.2.0/lib"
    "-Wl,-R/opt/gcc-15.2.0/lib"
    "-fopenmp"
    "-lstdc++exp"
    "-labsl_cordz_sample_token"
    "-labsl_failure_signal_handler"
    "-labsl_flags_parse"
    "-labsl_flags_usage"
    "-labsl_flags_usage_internal"
    "-labsl_log_flags"
    "-labsl_periodic_sampler"
    "-labsl_poison"
    "-labsl_random_internal_distribution_test_util"
    "-labsl_scoped_set_env"
    "-lboost_atomic"
    "-lboost_charconv"
    "-lboost_chrono"
    "-lboost_container"
    "-lboost_context"
    "-lboost_contract"
    "-lboost_coroutine"
    "-lboost_date_time"
    "-lboost_exception"
    "-lboost_fiber"
    "-lboost_filesystem"
    "-lboost_graph"
    "-lboost_iostreams"
    "-lboost_json"
    "-lboost_locale"
    "-lboost_log"
    "-lboost_log_setup"
    "-lboost_math_c99"
    "-lboost_math_c99f"
    "-lboost_math_c99l"
    "-lboost_math_tr1"
    "-lboost_math_tr1f"
    "-lboost_math_tr1l"
    "-lboost_nowide"
    "-lboost_prg_exec_monitor"
    "-lboost_process"
    "-lboost_program_options"
    "-lboost_random"
    "-lboost_regex"
    "-lboost_serialization"
    "-lboost_stacktrace_from_exception"
    "-lboost_system"
    "-lboost_test_exec_monitor"
    "-lboost_thread"
    "-lboost_timer"
    "-lboost_type_erasure"
    "-lboost_unit_test_framework"
    "-lboost_url"
    "-lboost_wave"
    "-lboost_wserialization"
    "-lgmpxx"
    "-lgmp"
    "-lortools"
    "-lCbc"
    "-lCbcSolver"
    "-lCgl"
    "-lClp"
    "-lClpSolver"
    "-lCoinUtils"
    "-lGLPK"
    "-lOsi"
    "-lOsiCbc"
    "-lOsiClp"
    "-lhighs"
    "-lscip"
    "-lz"
    "-lbz2"
    "-lprotobuf"
    "-labsl_die_if_null"
    "-labsl_log_initialize"
    "-labsl_random_distributions"
    "-labsl_random_seed_sequences"
    "-labsl_random_internal_entropy_pool"
    "-labsl_random_internal_randen"
    "-labsl_random_internal_randen_hwaes"
    "-labsl_random_internal_randen_hwaes_impl"
    "-labsl_random_internal_randen_slow"
    "-labsl_random_internal_platform"
    "-labsl_random_internal_seed_material"
    "-labsl_random_seed_gen_exception"
    "-labsl_statusor"
    "-labsl_status"
    "-lutf8_validity"
    "-lutf8_range"
    "-pthread"
    "-lre2"
    "-labsl_log_internal_check_op"
    "-labsl_leak_check"
    "-labsl_log_internal_conditions"
    "-labsl_log_internal_message"
    "-labsl_examine_stack"
    "-labsl_log_internal_format"
    "-labsl_log_internal_nullguard"
    "-labsl_log_internal_structured_proto"
    "-labsl_log_internal_proto"
    "-labsl_log_internal_log_sink_set"
    "-labsl_log_internal_globals"
    "-labsl_log_globals"
    "-labsl_log_sink"
    "-labsl_strerror"
    "-labsl_vlog_config_internal"
    "-labsl_log_internal_fnmatch"
    "-labsl_flags_internal"
    "-labsl_flags_marshalling"
    "-labsl_flags_reflection"
    "-labsl_flags_private_handle_accessor"
    "-labsl_flags_commandlineflag"
    "-labsl_flags_commandlineflag_internal"
    "-labsl_flags_config"
    "-labsl_flags_program_name"
    "-labsl_raw_hash_set"
    "-labsl_cord"
    "-labsl_cordz_info"
    "-labsl_cord_internal"
    "-labsl_cordz_functions"
    "-labsl_cordz_handle"
    "-labsl_crc_cord_state"
    "-labsl_crc32c"
    "-labsl_crc_internal"
    "-labsl_crc_cpu_detect"
    "-labsl_hashtablez_sampler"
    "-labsl_exponential_biased"
    "-labsl_hash"
    "-labsl_city"
    "-labsl_low_level_hash"
    "-labsl_str_format_internal"
    "-labsl_synchronization"
    "-labsl_graphcycles_internal"
    "-labsl_kernel_timeout_internal"
    "-labsl_stacktrace"
    "-labsl_symbolize"
    "-labsl_debugging_internal"
    "-labsl_demangle_internal"
    "-labsl_demangle_rust"
    "-labsl_decode_rust_punycode"
    "-labsl_utf8_for_code_point"
    "-labsl_malloc_internal"
    "-labsl_time"
    "-labsl_civil_time"
    "-labsl_strings"
    "-labsl_strings_internal"
    "-labsl_string_view"
    "-labsl_int128"
    "-labsl_throw_delegate"
    "-labsl_time_zone"
    "-labsl_tracing_internal"
    "-labsl_base"
    "-lrt"
    "-labsl_raw_logging_internal"
    "-labsl_log_severity"
    "-labsl_spinlock_wait"
    "-lz3"
    "-l_lightgbm"
    "-ltorch"
    "-ltorch_cpu"
    "-lc10")
    g++ ./Main.cpp -o a.out "${USER_BUILD_FLAGS[@]}"
    """
).strip()

NODE_MEMORY_KIB = 1048576  # 1 GiB


JUDGE_LANGUAGE_PROFILES: dict[str, dict[str, JudgeLanguageProfile]] = {
    "201907": {
        "cpp17": JudgeLanguageProfile(
            compile_command=(
                "g++ -std=gnu++17 -Wall -Wextra -O2 -DONLINE_JUDGE "
                "-I/opt/boost/gcc/include -L/opt/boost/gcc/lib -I/opt/ac-library -o a.out Main.cpp"
            ),
            run_command="./a.out",
            submission_file_path="Main.cpp",
            object_file_path="a.out",
        ),
        "python": JudgeLanguageProfile(
            compile_command="python3.8 -m py_compile Main.py; python3.8 Main.py ONLINE_JUDGE 2> /dev/null",
            run_command="python3.8 Main.py",
            submission_file_path="Main.py",
            object_file_path="__pycache__/Main.cpython-38.pyc",
        ),
        "rust": JudgeLanguageProfile(
            compile_command="RUST_BACKTRACE=0 cargo build --release --offline --quiet",
            run_command="./target/release/main",
            submission_file_path="src/main.rs",
            object_file_path="target/release/main",
        ),
    },
    "202301": {
        "cpp17": JudgeLanguageProfile(
            compile_command=(
                "g++ -std=gnu++17 -Wall -Wextra -O2 -DONLINE_JUDGE "
                "-I/opt/boost/gcc/include -L/opt/boost/gcc/lib -I/opt/ac-library -o a.out Main.cpp"
            ),
            run_command="./a.out",
            submission_file_path="Main.cpp",
            object_file_path="a.out",
        ),
        "cpp20": JudgeLanguageProfile(
            compile_command=(
                "g++-12 -std=gnu++20 -O2 -DONLINE_JUDGE -DATCODER -Wall -Wextra -mtune=native "
                "-march=native -fconstexpr-depth=2147483647 -fconstexpr-loop-limit=2147483647 "
                "-fconstexpr-ops-limit=2147483647 -I/opt/ac-library -I/opt/boost/gcc/include "
                "-L/opt/boost/gcc/lib -o a.out Main.cpp -lgmpxx -lgmp -I/usr/include/eigen3"
            ),
            run_command="./a.out",
            submission_file_path="Main.cpp",
            object_file_path="a.out",
        ),
        "cpp23": JudgeLanguageProfile(
            compile_command=(
                "g++-12 -std=gnu++2b -O2 -DONLINE_JUDGE -DATCODER -Wall -Wextra -mtune=native "
                "-march=native -fconstexpr-depth=2147483647 -fconstexpr-loop-limit=2147483647 "
                "-fconstexpr-ops-limit=2147483647 -I/opt/ac-library -I/opt/boost/gcc/include "
                "-L/opt/boost/gcc/lib -o a.out Main.cpp -lgmpxx -lgmp -I/usr/include/eigen3"
            ),
            run_command="./a.out",
            submission_file_path="Main.cpp",
            object_file_path="a.out",
        ),
        "python": JudgeLanguageProfile(
            compile_command="python3.11 -m py_compile Main.py; python3.11 Main.py ONLINE_JUDGE 2> /dev/null",
            run_command="python3.11 Main.py",
            submission_file_path="Main.py",
            object_file_path="__pycache__/Main.cpython-311.pyc",
        ),
        "rust": JudgeLanguageProfile(
            compile_command="RUST_BACKTRACE=0 cargo build --release --quiet --offline",
            run_command="./target/release/main",
            submission_file_path="src/main.rs",
            object_file_path="target/release/main",
        ),
    },
    "202510": {
        "bash": JudgeLanguageProfile(
            compile_command="bash -n Main.bash && printf 'ok\\n' > ok",
            run_command="bash Main.bash",
            submission_file_path="Main.bash",
            object_file_path="ok",
        ),
        # NOTE: 2025-10 C++ is intentionally fixed to the GCC profile in this repository.
        "cpp23": JudgeLanguageProfile(
            compile_command=CPP23_202510_COMPILE_COMMAND,
            run_command="./a.out",
            submission_file_path="Main.cpp",
            object_file_path="a.out",
        ),
        # NOTE: We execute the published DLL directly (`Main.dll`) instead of `./publish/Main`.
        "csharp": JudgeLanguageProfile(
            compile_command=(
                "export DOTNET_ROOT=/opt/dotnet; "
                "export PATH=/opt/dotnet:/opt/dotnet/tools:$PATH; "
                "export DOTNET_EnableWriteXorExecute=0; "
                "export DOTNET_CLI_TELEMETRY_OPTOUT=1; "
                "dotnet publish -c Release -o publish --no-restore --nologo -v q --tl:off 1>&2"
            ),
            run_command="dotnet publish/Main.dll",
            submission_file_path="Main.cs",
            object_file_path="publish/Main.dll",
        ),
        "fish": JudgeLanguageProfile(
            compile_command="fish -n Main.fish && printf 'ok\\n' > ok",
            run_command="fish Main.fish",
            submission_file_path="Main.fish",
            object_file_path="ok",
        ),
        # NOTE: We intentionally pin the compiler command to `gfortran-14`.
        "fortran": JudgeLanguageProfile(
            compile_command=(
                "gfortran-14 -I/workdir -I/usr/local/include -L/usr/local/lib -Wl,-rpath,/usr/local/lib "
                "-O2 -cpp -ffree-line-length-none -std=f2023 Main.f90 -lstdlib -o a.out"
            ),
            run_command="./a.out",
            submission_file_path="Main.f90",
            object_file_path="a.out",
        ),
        "go": JudgeLanguageProfile(
            compile_command="export PATH=$PATH:/opt/go/bin; env GOPROXY=off GO111MODULE=on go build -o a.out main.go",
            run_command="./a.out",
            submission_file_path="main.go",
            object_file_path="a.out",
        ),
        "haskell": JudgeLanguageProfile(
            compile_command=(
                "export PATH=/opt/.ghcup/bin:$PATH; "
                "cd submission; "
                "cabal v2-build --offline && cp $(cabal list-bin main) ../main"
            ),
            run_command="./main",
            submission_file_path="submission/app/Main.hs",
            object_file_path="main",
        ),
        "javascript": JudgeLanguageProfile(
            compile_command="node --check Main.js && printf 'ok\\n' > ok",
            run_command=f"sh node.sh {NODE_MEMORY_KIB} Main.js ONLINE_JUDGE ATCODER",
            submission_file_path="Main.js",
            object_file_path="ok",
        ),
        "julia": JudgeLanguageProfile(
            compile_command=(
                "export PATH=$PATH:/workdir/.juliaup/bin; "
                "export JULIA_DEPOT_PATH=/workdir/.julia; "
                'julia -e \'Meta.parse("begin " * read("Main.jl",String) * " end")\' '
                "&& printf 'ok\\n' > ok && julia Main.jl ONLINE_JUDGE 2> /dev/null"
            ),
            run_command="julia --threads=auto --startup-file=no --history-file=no Main.jl",
            submission_file_path="Main.jl",
            object_file_path="ok",
        ),
        "lean": JudgeLanguageProfile(
            compile_command="export PATH=/workdir/.elan/bin:$PATH; cd atcoder; lake -q build 1>&2",
            run_command="./atcoder/.lake/build/bin/atcoder",
            submission_file_path="atcoder/Main.lean",
            object_file_path="atcoder/.lake/build/bin/atcoder",
        ),
        "ocaml": JudgeLanguageProfile(
            compile_command=(
                'eval "$(opam env --switch=5.3.0+flambda)"; '
                "ocamlfind ocamlopt -O2 -o a.out "
                "main.ml -linkpkg -thread "
                "-package str,num,zarith,threads,containers,core,iter,batteries"
            ),
            run_command="./a.out",
            submission_file_path="main.ml",
            object_file_path="a.out",
        ),
        "perl": JudgeLanguageProfile(
            compile_command="perl -c Main.pl && printf 'ok\\n' > ok",
            run_command="perl Main.pl",
            submission_file_path="Main.pl",
            object_file_path="ok",
        ),
        "pypy": JudgeLanguageProfile(
            compile_command="pypy3 -m py_compile Main.py; pypy3 Main.py ONLINE_JUDGE 2> /dev/null",
            run_command="pypy3 -X int_max_str_digits=0 Main.py",
            submission_file_path="Main.py",
            object_file_path="__pycache__/Main.pypy311.pyc",
        ),
        "python": JudgeLanguageProfile(
            compile_command="python3.13 -m py_compile Main.py; python3.13 Main.py ONLINE_JUDGE 2> /dev/null",
            run_command="python3.13 -X int_max_str_digits=0 Main.py",
            submission_file_path="Main.py",
            object_file_path="__pycache__/Main.cpython-313.pyc",
        ),
        "rust": JudgeLanguageProfile(
            compile_command="RUST_BACKTRACE=0 cargo build --release --quiet --offline",
            run_command="./target/release/main",
            submission_file_path="src/main.rs",
            object_file_path="target/release/main",
        ),
        "typescript": JudgeLanguageProfile(
            compile_command=(
                "tsc Main.ts --target ESNext --moduleResolution nodenext --module NodeNext "
                "--noEmitOnError --pretty true | ansifilter 1>&2"
            ),
            run_command=f"sh node.sh {NODE_MEMORY_KIB} Main.js ONLINE_JUDGE ATCODER",
            submission_file_path="Main.ts",
            object_file_path="Main.js",
        ),
    },
}


ALL_CODE_LANGUAGES: set[str] = {
    "bash",
    "cpp17",
    "cpp20",
    "cpp23",
    "csharp",
    "fish",
    "fortran",
    "go",
    "haskell",
    "javascript",
    "julia",
    "lean",
    "ocaml",
    "perl",
    "pypy",
    "python",
    "rust",
    "typescript",
}


UNSUPPORTED_LANGUAGES_BY_JUDGE: dict[str, set[str]] = {
    judge_version: ALL_CODE_LANGUAGES - set(profile_by_lang.keys())
    for judge_version, profile_by_lang in JUDGE_LANGUAGE_PROFILES.items()
}
