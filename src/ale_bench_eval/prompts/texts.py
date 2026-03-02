import re
from string import Template

from ale_bench_eval.language_config import get_any_languages

_NO_LIBRARY_DOC_MESSAGE = "- No additional libraries are available."

CODE_LANGUAGE_STRING: dict[str, dict[str, str]] = {
    "201907": {
        "cpp17": "C++17 (GCC 9.2.0)",
        "python": "Python (CPython 3.8.2)",
        "rust": "Rust (rustc 1.42.0)",
    },
    "202301": {
        "cpp17": "C++17 (gcc 12.2.0)",
        "cpp20": "C++20 (gcc 12.2.0)",
        "cpp23": "C++23 (gcc 12.2.0)",
        "python": "Python (CPython 3.11.4)",
        "rust": "Rust (rustc 1.70.0)",
    },
    "202510": {
        "bash": "Bash (bash 5.3)",
        "cpp23": "C++23 (GCC 15.2.0)",
        "csharp": "C# 13.0 (.NET 9.0.8)",
        "fish": "Fish (fish 4.0.2)",
        "fortran": "Fortran2023 (GCC 14.2.0)",
        "go": "Go (go 1.25.1)",
        "haskell": "Haskell (GHC 9.8.4)",
        "javascript": "JavaScript (Node.js 22.19.0)",
        "julia": "Julia (Julia 1.11.6)",
        "lean": "Lean (lean v4.22.0)",
        "ocaml": "OCaml (ocamlopt 5.3.0)",
        "perl": "Perl (perl 5.38.2)",
        "pypy": "Python (PyPy 3.11-v7.3.20)",
        "python": "Python (CPython 3.13.7)",
        "rust": "Rust (rustc 1.89.0)",
        "typescript": "TypeScript (tsc 5.9.2 (Node.js 22.19.0))",
    },
}

CODE_LANGUAGE_LIBRARIES: dict[str, dict[str, str]] = {
    "201907": {
        "cpp17": """- AC Library@1.4
- Boost@1.72.0""",
        "python": """- Cython@3.0.12
- numba@0.58.1
- numpy@1.24.4
- scipy@1.10.1
- scikit-learn@1.3.2
- networkx@3.1""",
        "rust": """- num@=0.2.1
- num-bigint@=0.2.6
- num-complex@=0.2.4
- num-integer@=0.1.42
- num-iter@=0.1.40
- num-rational@=0.2.4
- num-traits@=0.2.11
- num-derive@=0.3.0
- ndarray@=0.13.0
- nalgebra@=0.20.0
- alga@=0.9.3
- libm@=0.2.1
- rand@=0.7.3
- getrandom@=0.1.14
- rand_chacha@=0.2.2
- rand_core@=0.5.1
- rand_hc@=0.2.0
- rand_pcg@=0.2.1
- rand_distr@=0.2.2
- petgraph@=0.5.0
- indexmap@=1.3.2
- regex@=1.3.6
- lazy_static@=1.4.0
- ordered-float@=1.0.2
- ascii@=1.0.0
- permutohedron@=0.2.4
- superslice@=1.0.0
- itertools@=0.9.0
- itertools-num@=0.1.3
- maplit@=1.0.2
- either@=1.5.3
- im-rc@=14.3.0
- fixedbitset@=0.2.0
- bitset-fixed@=0.1.0
- proconio@=0.3.6
- text_io@=0.1.8
- whiteread@=0.5.0
- rustc-hash@=1.1.0
- smallvec@=1.2.0""",
    },
    "202301": {
        "cpp17": """- AC Library@1.5.1
- Boost@1.82.0""",
        "cpp20": """- AC Library@1.5.1
- Boost@1.82.0
- GMP@6.2.1
- Eigen@3.4.0-2ubuntu2""",
        "cpp23": """- AC Library@1.5.1
- Boost@1.82.0
- GMP@6.2.1
- Eigen@3.4.0-2ubuntu2""",
        "python": """- numpy==1.24.1
- scipy==1.10.1
- networkx==3.0
- sympy==1.11.1
- sortedcontainers==2.4.0
- more-itertools==9.0.0
- shapely==2.0.0
- bitarray==2.6.2
- PuLP==2.7.0
- mpmath==1.2.1
- pandas==1.5.2
- z3-solver==4.12.1.0
- scikit-learn==1.2.0
- ortools==9.5.2237
- ac-library-python
- setuptools==66.0.0
- cppyy==2.4.1
- torch==1.13.1
- polars==0.15.15
- lightgbm==3.3.1
- gmpy2==2.1.5
- numba==0.57.0""",
        "rust": """- ac-library-rs@=0.1.1
- once_cell@=1.18.0
- static_assertions@=1.1.0
- varisat@=0.2.2
- memoise@=0.3.2
- argio@=0.2.0
- bitvec@=1.0.1
- counter@=0.5.7
- hashbag@=0.1.11
- pathfinding@=4.3.0
- recur-fn@=2.2.0
- indexing@=0.4.1
- amplify@=3.14.2
- amplify_derive@=2.11.3
- amplify_num@=0.4.1
- easy-ext@=1.0.1
- multimap@=0.9.0
- btreemultimap@=0.1.1
- bstr@=1.6.0
- az@=1.2.1
- glidesort@=0.1.2
- tap@=1.0.1
- omniswap@=0.1.0
- multiversion@=0.7.2
- num@=0.4.1
- num-bigint@=0.4.3
- num-complex@=0.4.3
- num-integer@=0.1.45
- num-iter@=0.1.43
- num-rational@=0.4.1
- num-traits@=0.2.15
- num-derive@=0.4.0
- ndarray@=0.15.6
- nalgebra@=0.32.3
- alga@=0.9.3
- libm@=0.2.7
- rand@=0.8.5
- getrandom@=0.2.10
- rand_chacha@=0.3.1
- rand_core@=0.6.4
- rand_hc@=0.3.2
- rand_pcg@=0.3.1
- rand_distr@=0.4.3
- petgraph@=0.6.3
- indexmap@=2.0.0
- regex@=1.9.1
- lazy_static@=1.4.0
- ordered-float@=3.7.0
- ascii@=1.1.0
- permutohedron@=0.2.4
- superslice@=1.0.0
- itertools@=0.11.0
- itertools-num@=0.1.3
- maplit@=1.0.2
- either@=1.8.1
- im-rc@=15.1.0
- fixedbitset@=0.4.2
- bitset-fixed@=0.1.0
- proconio@=0.4.5
- text_io@=0.1.12
- rustc-hash@=1.1.0
- smallvec@=1.11.0""",
    },
    "202510": {
        "bash": _NO_LIBRARY_DOC_MESSAGE,
        "cpp23": """- abseil = 20250512.1
- ac-library = 1.6
- boost = 1.88.0
- eigen = 3.4.0
- gmp = 6.3.0
- immer = 0.8.1
- libtorch = 2.8.0
- light-gbm = 4.6.0
- or-tools = 9.14
- range-v3 = 0.12.0
- unordered_dense = 4.5.0
- z3 = 4.15.2""",
        "csharp": """- MathNet.Numerics = 5.0.0
- Microsoft.ML = 4.0.2
- Microsoft.ML.LightGbm = 4.0.2
- ac-library-csharp = 3.9.2-atcoder1""",
        "fish": _NO_LIBRARY_DOC_MESSAGE,
        "fortran": """- ac-library-fortran =
- stdlib = v0.7.0""",
        "go": """- ac-library-go =
- gods =
- golang_org_x_exp =
- gonum =
- gostl =
- immutable =""",
        "haskell": """- Cabal = 3.16.0.0
- Cabal-syntax = 3.16.0.0
- QuickCheck = 2.16.0.0
- ac-library-hs = 1.5.3.0
- adjunctions = 4.4.3
- alex = 3.5.4.0
- array = 0.5.8.0
- attoparsec = 0.14.4
- base = 4.19.2.0
- bifunctors = 5.6.2
- binary = 0.8.9.3
- bitvec = 1.1.5.0
- bytestring = 0.12.2.0
- comonad = 5.0.9
- containers = 0.8
- contravariant = 1.5.5
- deepseq = 1.5.1.0
- directory = 1.3.9.0
- distributive = 0.6.2.1
- exceptions = 0.10.7
- extra = 1.8
- fgl = 5.8.3.0
- filepath = 1.4.301.0
- flow = 2.0.0.9
- free = 5.2
- ghc-bignum = 1.3
- ghc-prim = 0.11.0
- hashable = 1.5.0.0
- heaps = 0.4.1
- hmatrix = 0.20.2
- hmatrix-glpk = 0.19.0.0
- hmatrix-gsl = 0.19.0.1
- hmatrix-special = 0.19.0.0
- ilist = 0.4.0.1
- indexed-traversable = 0.1.4
- indexed-traversable-instances = 0.1.2
- integer-gmp = 1.1
- integer-logarithms = 1.0.4
- kan-extensions = 5.2.7
- lens = 5.3.5
- linear-base = 0.5.0
- list-t = 1.0.5.7
- massiv = 1.0.5.0
- megaparsec = 9.7.0
- monad-memo = 0.5.4
- mono-traversable = 1.0.21.0
- mtl = 2.3.1
- mutable-containers = 0.3.4.1
- mwc-random = 0.15.2.0
- parallel = 3.2.2.0
- parsec = 3.1.18.0
- parser-combinators = 1.3.0
- pretty = 1.1.3.6
- primitive = 0.9.1.0
- process = 1.6.26.1
- profunctors = 5.6.3
- psqueues = 0.2.8.2
- random = 1.3.1
- reflection = 2.1.9
- regex-tdfa = 1.3.2.4
- safe-exceptions = 0.1.7.4
- scientific = 0.3.8.0
- semialign = 1.3.1
- semigroupoids = 6.0.1
- split = 0.2.5
- stm = 2.5.3.1
- strict = 0.5.1
- strict-lens = 0.4.1
- tagged = 0.8.9
- tasty = 1.5.3
- template-haskell = 2.21.0.0
- text = 2.1.3
- tf-random = 0.5
- these = 1.2.1
- these-lens = 1.0.2
- time = 1.12.2
- transformers = 0.6.1.0
- trifecta = 2.1.4
- unboxing-vector = 0.2.0.0
- unix = 2.8.6.0
- unordered-containers = 0.2.20
- utility-ht = 0.0.17.2
- vector = 0.13.2.0
- vector-algorithms = 0.9.1.0
- vector-split = 1.0.0.4
- vector-stream = 0.1.0.1
- vector-th-unbox = 0.2.2
- wide-word = 0.1.7.1
- witherable = 0.5
- xhtml = 3000.2.2.1""",
        "javascript": """- ac-library-js = 0.1.1
- data-structure-typed = 2.0.4
- immutable = 5.1.3
- lodash = 4.17.21
- mathjs = 14.7.0
- tstl = 3.0.0""",
        "julia": """- Combinatorics = v1.0.3
- DataStructures = v0.18.22
- DelimitedFiles = v1.9.1
- Distributions = v0.25.120
- InvertedIndices = v1.3.1
- IterTools = v1.10.0
- OffsetArrays = v1.17.0
- PrecompileTools = v1.2.1
- Primes = v0.5.7
- StaticArrays = v1.9.14""",
        "lean": """- lean-regex = v4.22.0
- mathlib = v4.22.0
- parser = 617f4fa""",
        "ocaml": """- batteries = 3.9.0
- containers = 3.16
- core = v0.17.1
- iter = 1.9
- num = 1.6
- ocaml-option-flambda = 1
- zarith = 1.14""",
        "perl": _NO_LIBRARY_DOC_MESSAGE,
        "pypy": """- PuLP = v3.2.2
- ac-library-python =
- acl-cpp-python = v0.6.2
- bitarray = v3.6.0
- cppyy = v3.5.0
- more-itertools = v10.7.0
- mpmath = v1.3.0
- networkx = v3.5
- numpy = v2.3.2
- pandas = v2.3.1
- scikit-learn = v1.7.1
- scipy = v1.15.3
- shapely = v2.1.1
- sortedcontainers = v2.4.0
- sympy = v1.14.0
- z3-solver = v4.15.1.0""",
        "python": """- CPyCppyy = v1.13.0
- Cython = v3.1.3
- Jinja2 = v3.1.6
- MarkupSafe = v3.0.2
- PuLP = v3.2.2
- absl-py = v2.3.1
- ac-library-python =
- acl-cpp-python = v0.6.2
- bitarray = v3.6.1
- cppyy = v3.5.0
- cppyy-backend = v1.15.3
- cppyy-cling = v6.32.8
- filelock = v3.19.1
- fsspec = 2025.7.0
- gmpy2 = v2.2.1
- immutabledict = v4.2.1
- joblib = v1.5.1
- lightgbm = v4.6.0
- llvmlite = v0.44.0
- more-itertools = v10.7.0
- mpmath = v1.3.0
- networkx = v3.5
- numba = v0.61.2
- numpy = v2.2.6
- ortools = v9.14.6206
- pandas = v2.3.2
- polars = v1.31.0
- protobuf = v6.31.1
- pyrsistent = v0.20.0
- python-dateutil = v2.9.0.post0
- pytz = v2025.2
- rustworkx = v0.16.0
- scikit-learn = v1.7.1
- scipy = v1.16.1
- shapely = v2.1.1
- six = v1.17.0
- sortedcontainers = v2.4.0
- sympy = v1.14.0
- threadpoolctl = v3.6.0
- torch = v2.8.0+cpu
- typing_extensions = v4.14.1
- tzdata = v2025.2
- z3-solver = v4.15.3.0""",
        "rust": """- ac-library-rs-0-2-0 = 0.2.0
- alga-0-9-3 = 0.9.3
- amplify-4-9-0 = 4.9.0
- amplify_derive-4-0-1 = 4.0.1
- amplify_num-0-5-3 = 0.5.3
- argio-0-2-0 = 0.2.0
- ascii-1-1-0 = 1.1.0
- az-1-2-1 = 1.2.1
- bitset-fixed-0-1-0 = 0.1.0
- bitvec-1-0-1 = 1.0.1
- bstr-1-12-0 = 1.12.0
- btreemultimap-0-1-1 = 0.1.1
- counter-0-7-0 = 0.7.0
- easy-ext-1-0-2 = 1.0.2
- either-1-15-0 = 1.15.0
- fixedbitset-0-5-7 = 0.5.7
- getrandom-0-3-3 = 0.3.3
- glidesort-0-1-2 = 0.1.2
- hashbag-0-1-12 = 0.1.12
- im-rc-15-1-0 = 15.1.0
- indexing-0-4-1 = 0.4.1
- indexmap-2-11-0 = 2.11.0
- itertools-0-14-0 = 0.14.0
- itertools-num-0-1-3 = 0.1.3
- lazy_static-1-5-0 = 1.5.0
- libm-0-2-15 = 0.2.15
- maplit-1-0-2 = 1.0.2
- memoise-0-3-2 = 0.3.2
- multimap-0-10-1 = 0.10.1
- multiversion-0-8-0 = 0.8.0
- nalgebra-0-34-0 = 0.34.0
- ndarray-0-16-1 = 0.16.1
- num-0-4-3 = 0.4.3
- num-bigint-0-4-6 = 0.4.6
- num-complex-0-4-6 = 0.4.6
- num-derive-0-4-2 = 0.4.2
- num-integer-0-1-46 = 0.1.46
- num-iter-0-1-45 = 0.1.45
- num-rational-0-4-2 = 0.4.2
- num-traits-0-2-19 = 0.2.19
- omniswap-0-1-0 = 0.1.0
- once_cell-1-21-3 = 1.21.3
- ordered-float-5-0-0 = 5.0.0
- pathfinding-4-14-0 = 4.14.0
- permutohedron-0-2-4 = 0.2.4
- petgraph-0-8-2 = 0.8.2
- primal-0-3-3 = 0.3.3
- proconio-0-5-0 = 0.5.0
- rand-0-9-2 = 0.9.2
- rand_chacha-0-9-0 = 0.9.0
- rand_core-0-9-3 = 0.9.3
- rand_distr-0-5-1 = 0.5.1
- rand_hc-0-4-0 = 0.4.0
- rand_pcg-0-9-0 = 0.9.0
- rand_xorshift-0-4-0 = 0.4.0
- rand_xoshiro-0-7-0 = 0.7.0
- recur-fn-2-2-0 = 2.2.0
- regex-1-11-2 = 1.11.2
- rpds-1-1-1 = 1.1.1
- rustc-hash-2-1-1 = 2.1.1
- smallvec-1-15-1 = 1.15.1
- static_assertions-1-1-0 = 1.1.0
- statrs-0-18-0 = 0.18.0
- superslice-1-0-0 = 1.0.0
- tap-1-0-1 = 1.0.1
- text_io-0-1-13 = 0.1.13
- thiserror-2-0-16 = 2.0.16
- varisat-0-2-2 = 0.2.2""",
        "typescript": """- @types/lodash = 4.17.20
- @types/node = 22.18.1
- ac-library-js = 0.1.1
- data-structure-typed = 2.0.4
- immutable = 5.1.3
- lodash = 4.17.21
- mathjs = 14.7.0
- tstl = 3.0.0
- typescript = 5.9.2""",
    },
}

CODE_BLOCK_LANGUAGE_NAME = {
    "bash": "bash",
    "cpp17": "cpp",
    "cpp20": "cpp",
    "cpp23": "cpp",
    "csharp": "csharp",
    "fish": "fish",
    "fortran": "fortran",
    "go": "go",
    "haskell": "haskell",
    "javascript": "javascript",
    "julia": "julia",
    "lean": "lean",
    "ocaml": "ocaml",
    "perl": "perl",
    "pypy": "pypy",
    "python": "python",
    "rust": "rust",
    "typescript": "typescript",
    "markdown": "md",
}

CODE_BLOCK_STRING = {
    language: f"```{language_name} ```"
    for language, language_name in CODE_BLOCK_LANGUAGE_NAME.items()
}

CODE_BLOCK_MATCH = {
    language: re.compile(rf"```{language_name}\s*\n(.+?)\n```", re.DOTALL)  # NOTE: Slightly changed to allow \s characters after the language name
    for language, language_name in CODE_BLOCK_LANGUAGE_NAME.items()
}


def _get_language_value(table: dict[str, dict[str, str]], judge_version: str, code_language: str, key_name: str) -> str:
    table_by_judge = table.get(judge_version)
    if table_by_judge is None:
        msg = f"Unsupported judge version for {key_name}: {judge_version}"
        raise ValueError(msg)
    value = table_by_judge.get(code_language)
    if value is None:
        msg = f"Unsupported code language for judge version {judge_version} in {key_name}: {code_language}"
        raise ValueError(msg)
    return value


def get_code_language_string(code_language: str, judge_version: str) -> str:
    return _get_language_value(CODE_LANGUAGE_STRING, judge_version, code_language, "code_language_string")


def get_code_language_libraries(code_language: str, judge_version: str) -> str:
    return _get_language_value(CODE_LANGUAGE_LIBRARIES, judge_version, code_language, "code_language_libraries")


def get_code_language_string_any(judge_version: str) -> str:
    return ", ".join(get_code_language_string(lang, judge_version) for lang in get_any_languages(judge_version))


def get_code_language_libraries_any(judge_version: str) -> str:
    return "\n".join(
        f"[{get_code_language_string(lang, judge_version)}]\n{get_code_language_libraries(lang, judge_version)}"
        for lang in get_any_languages(judge_version)
    )


def get_code_block_string_any(judge_version: str) -> str:
    return "\n".join(
        f"- {get_code_language_string(lang, judge_version)}: {CODE_BLOCK_STRING[lang]}"
        for lang in get_any_languages(judge_version)
    )

SYSTEM_PROMPT = {
    "en": (
        "You are a world-class algorithm engineer, and you are very good at programming. "
        "Now, you are participating in a programming contest. "
        "You are asked to solve a heuristic problem, known as an NP-hard problem."
    ),
    "ja": (
        "あなたは世界トップクラスのアルゴリズムエンジニアであり、プログラミングがとても得意です。"
        "今、あなたはプログラミングコンテストに参加しています。"
        "あなたはNP困難問題として知られるヒューリスティック問題を解くよう求められています。"
    ),
}

CONSIDERATION_PROMPT = {
    "en": (
        "There is a problem statement at the end of this message. "
        "First, please analyze the problem statement. "
        "Please think about the essential points of the problem and possible algorithms to get higher rank in the contest. "
    ),
    "ja": (
        "このメッセージの最後に問題文があります。"
        "まず、問題文を分析してください。"
        "問題の本質的なポイントと、コンテストでより高い順位を得る可能性のあるアルゴリズムについて考えてください。"
    ),
}
IMPLEMENTATION_ANY_PROMPT = {
    "en": Template(
        "Next, please implement your solution in any of the following languages: ${language_strings}. "
        "Your solution code should be written in the specified code block as follows:\n${code_blocks}\n"
        "You can use external libraries for each language. "
        "The available libraries are as follows:\n${libraries}\n\n"
    ),
    "ja": Template(
        "続いて、次のいずれかの言語で解法を実装してください: ${language_strings}。"
        "解法コードは、次のように指定されたコードブロックに記述してください:\n${code_blocks}\n"
        "各言語で外部ライブラリを使用できます。"
        "使用可能なライブラリは次の通りです:\n${libraries}\n\n"
    ),
}
IMPLEMENTATION_SPECIFIC_PROMPT = {
    "en": Template(
        "Next, please implement your solution in ${language}. "
        "Your solution code should be written in the ${code_block} code block. "
        "You can use external libraries as follows:\n${libraries}\n\n"
    ),
    "ja": Template(
        "続いて、${language}で解法を実装してください。"
        "解法コードは、${code_block}コードブロックに記述してください。"
        "使用可能なライブラリは次の通りです:\n${libraries}\n\n"
    ),
}
PROBLEM_HEADER_PROMPT = {
    "en": Template(
        "[Problem statement]\n"
        "Execution time limit: ${time_limit} sec / Memory limit: ${memory_limit} MiB\n"
    ),
    "ja": Template(
        "[問題文]\n実行時間制限: ${time_limit} sec / メモリ制限: ${memory_limit} MiB\n"
    ),
}

NO_CODE_BLOCK_ANY_PROMPT = {
    "en": Template(
        "No valid code block found. "
        "Please implement your solution in any of the following languages: ${language_strings}. "
        "Your solution code should be written in the specified code block as follows:\n${code_blocks}"
    ),
    "ja": Template(
        "有効なコードブロックが見つかりませんでした。"
        "次のいずれかの言語で解法を実装してください: ${language_strings}。"
        "解法コードは、次のように指定されたコードブロックに記述してください:\n${code_blocks}"
    ),
}
NO_CODE_BLOCK_SPECIFIC_PROMPT = {
    "en": Template(
        "No valid code block found. "
        "Please implement your solution in ${language}. "
        "Your solution code should be written in the ${code_block} code block."
    ),
    "ja": Template(
        "有効なコードブロックが見つかりませんでした。"
        "${language}で解法を実装してください。"
        "解法コードは、${code_block}コードブロックに記述してください。"
    ),
}

FEEDBACK_PROMPT = {
    "en": Template(
        "${feedback}\n\n"
        "Based on the above feedback, please consider the ways to improve your solution. "
        "Firstly, please analyze this given feedback and list what insights can be gained from it. "
        "Then, based on the insights, please refine your code to achieve better performance. "
        "It can be a simple bug fix, the introduction of a new algorithm, or any degree of change from minor to major. "
    ),
    "ja": Template(
        "${feedback}\n\n"
        "上記のフィードバックをもとに、解法を改善する方法を考えてください。"
        "まず、このフィードバックを分析し、そこから得られる洞察を列挙してください。"
        "次に、その洞察に基づいて、より良いパフォーマンスを達成するためにコードを改良してください。"
        "単純なバグ修正、新しいアルゴリズムの導入、または小さな変更から大きな変更まで、どの程度の変更でも構いません。"
    ),
}
FEEDBACK_PROMPT_WITH_SUMMARY = {
    "en": Template(
        "\n\n[Summary of your previous attempts]\n"
        "${action_summary}\n\n"
        "[Your best submission]\n"
        "### Code\n"
        "${best_code}\n\n"
        "### Feedback\n"
        "${best_feedback}\n\n"
        "[Your latest submission]\n"
        "### Code\n"
        "${latest_code}\n\n"
        "### Feedback\n"
        "${latest_feedback}\n\n"
        "Based on the above feedback, please consider the ways to improve your solution. "
        "Firstly, please analyze this given feedback and list what insights can be gained from it. "
        "Apart from that, please create a new summary including the content of the summary of your previous attempts in Markdown format in the ${summary_code_block} code block. "
        "If this code block in this format is not found, the summary of your previous attempts will not be input in the next turn. "
        "Then, based on the insights, please refine your code to achieve better performance. "
        "It can be a simple bug fix, the introduction of a new algorithm, or any degree of change from minor to major. "
    ),
    "ja": Template(
        "\n\n[あなたの過去の試行の要約]\n"
        "${action_summary}\n\n"
        "[あなたのベスト提出]\n"
        "### コード\n"
        "${best_code}\n\n"
        "### フィードバック\n"
        "${best_feedback}\n\n"
        "[あなたの最新の提出]\n"
        "### コード\n"
        "${latest_code}\n\n"
        "### フィードバック\n"
        "${latest_feedback}\n\n"
        "上記のフィードバックをもとに、解法を改善する方法を考えてください。"
        "まず、このフィードバックを分析し、そこから得られる洞察を列挙してください。"
        "またそれとは別に、これまでの試行の要約の内容も含めた新しい要約をMarkdown形式で${summary_code_block}コードブロックに記述してください。"
        "この様式のコードブロックが見つからない場合、次のターンにおけるあなたの過去の試行の要約は入力されません。"
        "次に、その洞察に基づいて、より良いパフォーマンスを達成するためにコードを改良してください。"
        "単純なバグ修正、新しいアルゴリズムの導入、または小さな変更から大きな変更まで、どの程度の変更でも構いません。"
    ),
}
REFINE_ANY_PROMPT = {
    "en": Template(
        "Your solution code should be written in the specified code block as follows:\n${code_blocks}"
    ),
    "ja": Template(
        "解法コードは、次のように指定されたコードブロックに記述してください:\n${code_blocks}"
    ),
}
REFINE_SPECIFIC_PROMPT = {
    "en": Template(
        "Your solution code should be written in the ${code_block} code block."
    ),
    "ja": Template("解法コードは、${code_block}コードブロックに記述してください。"),
}
NO_SUMMARY_PROMPT = {
    "en": "Your summary was not found. The summary must be written in the Markdown format in the ```md ``` code block.",
    "ja": "あなたの要約は見つかりませんでした。要約は必ずMarkdown形式で```md ```コードブロックに記述してください。",
}
