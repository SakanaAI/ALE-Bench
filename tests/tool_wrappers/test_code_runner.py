from __future__ import annotations

import pytest

from ale_bench.result import CodeRunResult
from ale_bench.tool_wrappers.code_runner import ExitStatus, parse_profiles

sample_profiles_content = """{{
    "command": "dummy command",
    "exit_status": "{}",
    "elapsed_time": "{}",
    "elapsed_time_seconds": "{}",
    "system_cpu_seconds": "{}",
    "user_cpu_seconds": "{}",
    "cpu_percent": "100%",
    "average_resident_set_size_kbytes": "0",
    "max_resident_set_size_kbytes": "{}",
    "average_total_memory_kbytes": "0",
    "signals_delivered": "0",
    "page_size_bytes": "4096",
    "minor_page_faults": "128",
    "major_page_faults": "0",
    "swaps": "0",
    "file_system_inputs": "0",
    "file_system_outputs": "0",
    "average_shared_text_kbytes": "0",
    "average_unshared_data_kbytes": "0",
    "average_unshared_stack_kbytes": "0",
    "voluntary_context_switches": "0",
    "involuntary_context_switches": "0",
    "socket_messages_sent": "0",
    "socket_messages_received": "0"
}}"""


@pytest.mark.parametrize(
    "time_limit,memory_limit,execution_time_host,profiles_content,expected",
    [
        pytest.param(
            2.0,
            1073741824,
            2.01,
            "",
            CodeRunResult(
                stdin="",
                stdout="",
                stderr="",
                exit_status=ExitStatus.TIME_LIMIT_EXCEEDED.value,
                execution_time=2.01,
                memory_usage=0,
            ),
            id="empty_tle",
        ),
        pytest.param(
            2.0,
            1073741824,
            2.2,
            "",
            CodeRunResult(
                stdin="",
                stdout="",
                stderr="",
                exit_status=ExitStatus.TIME_LIMIT_EXCEEDED.value,
                execution_time=2.1,
                memory_usage=0,
            ),
            id="empty_tle_too_long",
        ),
        pytest.param(
            2.0,
            1073741824,
            0.9,
            "",
            CodeRunResult(
                stdin="",
                stdout="",
                stderr="",
                exit_status=ExitStatus.RUNTIME_ERROR.value,
                execution_time=0.9,
                memory_usage=0,
            ),
            id="empty_re",
        ),
        pytest.param(
            2.0,
            1073741824,
            2.0,
            "",
            CodeRunResult(
                stdin="",
                stdout="",
                stderr="",
                exit_status=ExitStatus.RUNTIME_ERROR.value,
                execution_time=2.0,
                memory_usage=0,
            ),
            id="empty_re_time_limit",
        ),
        pytest.param(
            2.0,
            1073741824,
            1.99,
            sample_profiles_content.format("0", "0:02.23", "2.23", "0.23", "2.00", "16384")[:-10],
            CodeRunResult(
                stdin="",
                stdout="",
                stderr="Failed to parse profiles.\nStandard error:\n",
                exit_status=ExitStatus.RUNTIME_ERROR.value,
                execution_time=1.99,
                memory_usage=0,
            ),
            id="broken_wa",
        ),
        pytest.param(
            2.0,
            1073741824,
            2.2,
            sample_profiles_content.format("0", "0:02.23", "2.23", "0.23", "2.00", "16384")[:-10],
            CodeRunResult(
                stdin="",
                stdout="",
                stderr="Failed to parse profiles.\nStandard error:\n",
                exit_status=ExitStatus.RUNTIME_ERROR.value,
                execution_time=2.1,
                memory_usage=0,
            ),
            id="broken_wa_too_long",
        ),
        pytest.param(
            2.0,
            1073741824,
            1.99,
            (
                "Command terminated by signal 9.\n"
                f"{sample_profiles_content.format('0', '0:02.23', '2.23', '0.23', '2.00', '16384')[:-10]}"
            ),
            CodeRunResult(
                stdin="",
                stdout="",
                stderr="Failed to parse profiles.\nStandard error:\n",
                exit_status=ExitStatus.RUNTIME_ERROR.value,
                execution_time=1.99,
                memory_usage=0,
            ),
            id="killed_broken_wa",
        ),
        pytest.param(
            2.0,
            1073741824,
            1.99,
            (
                "Command exited with non-zero status.\n"
                f"{sample_profiles_content.format('0', '0:02.23', '2.23', '0.23', '2.00', '16384')[:-10]}"
            ),
            CodeRunResult(
                stdin="",
                stdout="",
                stderr="Failed to parse profiles.\nStandard error:\n",
                exit_status=ExitStatus.RUNTIME_ERROR.value,
                execution_time=1.99,
                memory_usage=0,
            ),
            id="non_zero_exited_broken_wa",
        ),
        pytest.param(
            2.0,
            1073741824,
            1.99,
            (
                "Command terminated by signal 9.\n.\n"
                f"{sample_profiles_content.format('0', '0:02.23', '2.23', '0.23', '2.00', '16384')[:-10]}"
            ),
            CodeRunResult(
                stdin="",
                stdout="",
                stderr="Failed to parse profiles.\nStandard error:\n",
                exit_status=ExitStatus.RUNTIME_ERROR.value,
                execution_time=1.99,
                memory_usage=0,
            ),
            id="invalid_profiles_content_wa",
        ),
        pytest.param(
            2.0,
            1073741824,
            1.99,
            "\n".join(sample_profiles_content.format("0", "0:02.23", "2.23", "0.23", "2.00", "16384").splitlines()[:-3])
            + '    "socket_messages_received": "0"\n}\n',
            CodeRunResult(
                stdin="",
                stdout="",
                stderr="Invalid profiles format.\nStandard error:\n",
                exit_status=ExitStatus.RUNTIME_ERROR.value,
                execution_time=1.99,
                memory_usage=0,
            ),
            id="invalid_profiles_format_ie",
        ),
        pytest.param(
            2.0,
            1073741824,
            2.11,
            "\n".join(sample_profiles_content.format("0", "0:02.23", "2.23", "0.23", "2.00", "16384").splitlines()[:-3])
            + '    "socket_messages_received": "0"\n}\n',
            CodeRunResult(
                stdin="",
                stdout="",
                stderr="Invalid profiles format.\nStandard error:\n",
                exit_status=ExitStatus.RUNTIME_ERROR.value,
                execution_time=2.1,
                memory_usage=0,
            ),
            id="invalid_profiles_format_ie_too_long",
        ),
        pytest.param(
            2.0,
            1073741824,
            1.99,
            sample_profiles_content.format("1", "0:01.23", "1.23", "0.23", "1.00", "16384"),
            CodeRunResult(
                stdin="",
                stdout="",
                stderr="",
                exit_status=1,
                execution_time=1.23,
                memory_usage=16777216,
            ),
            id="exited_non_zero_status_re",
        ),
        pytest.param(
            2.0,
            1073741824,
            1.99,
            sample_profiles_content.format("9", "0:02.23", "2.23", "0.23", "1.00", "16384"),
            CodeRunResult(
                stdin="",
                stdout="",
                stderr="",
                exit_status=9,
                execution_time=2.1,
                memory_usage=16777216,
            ),
            id="exited_non_zero_status_re_too_long",
        ),
        pytest.param(
            2.0,
            1073741824,
            1.99,
            sample_profiles_content.format("0", "0:02.01", "2.01", "0.01", "2.00", "16384"),
            CodeRunResult(
                stdin="",
                stdout="",
                stderr="",
                exit_status=ExitStatus.TIME_LIMIT_EXCEEDED.value,
                execution_time=2.01,
                memory_usage=16777216,
            ),
            id="tle",
        ),
        pytest.param(
            2.0,
            1073741824,
            1.99,
            sample_profiles_content.format("0", "0:02.23", "2.23", "0.23", "2.00", "16384"),
            CodeRunResult(
                stdin="",
                stdout="",
                stderr="",
                exit_status=ExitStatus.TIME_LIMIT_EXCEEDED.value,
                execution_time=2.1,
                memory_usage=16777216,
            ),
            id="tle_too_long",
        ),
        pytest.param(
            2.0,
            1073741824,
            1.99,
            sample_profiles_content.format("0", "0:02.01", "2.01", "0.01", "2.00", "1048577"),
            CodeRunResult(
                stdin="",
                stdout="",
                stderr="",
                exit_status=ExitStatus.TIME_LIMIT_EXCEEDED.value,
                execution_time=2.01,
                memory_usage=1073742848,
            ),
            id="tle_too_many_memory",
        ),
        pytest.param(
            2.0,
            1073741824,
            1.99,
            (
                "Command terminated by signal 9.\n"
                f"{sample_profiles_content.format('0', '0:02.00', '2.00', '0.00', '2.00', '16384')}"
            ),
            CodeRunResult(
                stdin="",
                stdout="",
                stderr="",
                exit_status=ExitStatus.TIME_LIMIT_EXCEEDED.value,
                execution_time=2.00,
                memory_usage=16777216,
            ),
            id="killed_tle",
        ),
        pytest.param(
            2.0,
            1073741824,
            1.99,
            sample_profiles_content.format("0", "0:02.00", "2.00", "0.00", "2.00", "1048577"),
            CodeRunResult(
                stdin="",
                stdout="",
                stderr="",
                exit_status=ExitStatus.MEMORY_LIMIT_EXCEEDED.value,
                execution_time=2.00,
                memory_usage=1073742848,
            ),
            id="mle",
        ),
        pytest.param(
            2.0,
            1073741824,
            1.99,
            sample_profiles_content.format("0", "0:02.00", "2.00", "0.00", "2.00", "16384"),
            (2.0, 16777216),
            id="ac",
        ),
        pytest.param(
            2.0,
            1073741824,
            1.99,
            sample_profiles_content.format("0", "0:02.00", "2.00", "0.00", "2.00", "1048576"),
            (2.0, 1073741824),
            id="ac_memory_limit",
        ),
        pytest.param(
            2.0,
            1073741824,
            2.01,
            sample_profiles_content.format("0", "0:02.00", "2.00", "0.00", "2.00", "1048576"),
            (2.0, 1073741824),
            id="ac_ignore_host_time",
        ),
    ],
)
def test_parse_profiles(
    time_limit: float,
    memory_limit: int,
    execution_time_host: float,
    profiles_content: str,
    expected: CodeRunResult | tuple[float, int],
) -> None:
    assert parse_profiles(time_limit, memory_limit, profiles_content, execution_time_host, "", "", "") == expected
