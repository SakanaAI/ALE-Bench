import re
from string import Template

ANY_CODE_LANGUAGES = ["cpp20", "python", "rust"]

CODE_LANGUAGE_STRING = {
    "cpp17": "C++17 (gcc 12.2.0)",
    "cpp20": "C++20 (gcc 12.2.0)",
    "cpp23": "C++23 (gcc 12.2.0)",
    "python": "Python (CPython 3.11.4)",
    "rust": "Rust (rustc 1.70.0)",
}
CODE_LANGUAGE_STRING_ANY = ", ".join(
    CODE_LANGUAGE_STRING[lang]
    for lang in CODE_LANGUAGE_STRING
    if lang in ANY_CODE_LANGUAGES
)

CODE_LANGUAGE_LIBRARIES = {
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
}
CODE_LANGUAGE_LIBRARIES_ANY = "\n".join(
    [
        f"[{CODE_LANGUAGE_STRING[lang]}]\n{lib}"
        for lang, lib in CODE_LANGUAGE_LIBRARIES.items()
        if lang in ANY_CODE_LANGUAGES
    ]
)

CODE_BLOCK_LANGUAGE_NAME = {
    "cpp17": "cpp",
    "cpp20": "cpp",
    "cpp23": "cpp",
    "python": "python",
    "rust": "rust",
    "markdown": "md",
}

CODE_BLOCK_STRING = {
    "cpp17": "```cpp ```",
    "cpp20": "```cpp ```",
    "cpp23": "```cpp ```",
    "python": "```python ```",
    "rust": "```rust ```",
    "markdown": "```md ```",
}
CODE_BLOCK_STRING_ANY = "\n".join(
    [
        f"- {CODE_LANGUAGE_STRING[lang]}: {block}"
        for lang, block in CODE_BLOCK_STRING.items()
        if lang in ANY_CODE_LANGUAGES
    ]
)

CODE_BLOCK_MATCH = {
    "cpp17": re.compile(r"```cpp\n(.+?)\n```", re.DOTALL),
    "cpp20": re.compile(r"```cpp\n(.+?)\n```", re.DOTALL),
    "cpp23": re.compile(r"```cpp\n(.+?)\n```", re.DOTALL),
    "python": re.compile(r"```python\n(.+?)\n```", re.DOTALL),
    "rust": re.compile(r"```rust\n(.+?)\n```", re.DOTALL),
    "markdown": re.compile(r"```md\n(.+?)\n```", re.DOTALL),
}

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
