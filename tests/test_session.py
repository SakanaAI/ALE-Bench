from __future__ import annotations

import datetime as dt
import json
import tempfile
from contextlib import AbstractContextManager, nullcontext as does_not_raise
from pathlib import Path
from typing import Any

import pytest
from pytest_mock.plugin import MockerFixture

from ale_bench.code_language import CodeLanguage, JudgeVersion
from ale_bench.data import (
    Problem,
    ProblemConstraints,
    ProblemMetaData,
    ProblemType,
    RankPerformanceMap,
    ScoreType,
    Standings,
)
from ale_bench.error import AleBenchError
from ale_bench.result import CaseResult, JudgeResult, ResourceUsage
from ale_bench.session import AleBenchFunction, Session


@pytest.fixture(scope="function")
def ale_bench_session_mocker(mocker: MockerFixture) -> None:
    mocker.patch("ale_bench.session.generate_inputs", return_value=["dummy input 1", "dummy input 2", "dummy input 3"])
    mocker.patch(
        "ale_bench.session.run_cases",
        return_value=[
            CaseResult(
                judge_result=JudgeResult.ACCEPTED,
                message="",
                absolute_score=1000000000,
                execution_time=4.9,
                memory_usage=16 * 1024 * 1024,
            ),
            CaseResult(
                judge_result=JudgeResult.ACCEPTED,
                message="",
                absolute_score=998244353,
                execution_time=4.8,
                memory_usage=16 * 1024 * 1024,
            ),
            CaseResult(
                judge_result=JudgeResult.ACCEPTED,
                message="",
                absolute_score=999999999,
                execution_time=4.7,
                memory_usage=16 * 1024 * 1024,
            ),
        ],
    )
    mocker.patch("ale_bench.session.local_visualization", return_value=[None])


@pytest.fixture(scope="function")
def dummy_session(ale_bench_session_mocker: None) -> Session:
    session = Session(
        problem=Problem(
            metadata=ProblemMetaData(
                problem_id="ahc001",
                start_at=dt.datetime(2021, 3, 6, 12, 0, tzinfo=dt.timezone(dt.timedelta(hours=9))),
                end_at=dt.datetime(2021, 3, 14, 20, 0, tzinfo=dt.timezone(dt.timedelta(hours=9))),
                contest_url="https://atcoder.jp/contests/ahc001",
                title="AtCoder Ad",
                problem_type=ProblemType.BATCH,
                score_type=ScoreType.MAXIMIZE,
            ),
            constraints=ProblemConstraints(time_limit=5.0, memory_limit=1073741824),
            statement="dummy statement",
            statement_ja="dummy statement in Japanese",
            statement_images={},
            example_input="dummy input",
            example_output="dummy output",
            tool_readme="dummy tool README",
        ),
        lite_version=False,
        public_seeds=[0, 1, 2],
        private_seeds=[3, 4, 5],
        standings=Standings(standings_scores=[(1, 3000000000), (2, 2700000000), (3, 2400000000), (4, 0)]),
        rank_performance_map=RankPerformanceMap(raw_data=[(1, 3200), (2, 2800), (3, 2400), (4, 100)]),
        tool_dir=Path("/tmp/dummy"),
        use_same_time_scale=True,
        maximum_resource_usage=ResourceUsage(
            num_case_gen=5,
            num_case_eval=5,
            execution_time_case_eval=60.0,  # seconds
            num_call_public_eval=3,  # number of public evaluations
            num_call_private_eval=1,
        ),
        session_duration=dt.timedelta(seconds=3600),  # 1 hour
        num_workers=1,
        visualization_server_port=None,
    )
    return session


class TestSession:
    def test_repr(self, dummy_session: Session) -> None:
        assert str(dummy_session) == "Session(problem_id=ahc001)"
        assert repr(dummy_session) == "Session(problem_id=ahc001)"

    @pytest.mark.parametrize(
        "current_resource_usage,utc_now,context",
        [
            pytest.param(
                ResourceUsage(), dt.datetime(2000, 1, 1, 0, 30, tzinfo=dt.timezone.utc), does_not_raise(), id="ok"
            ),
            pytest.param(
                ResourceUsage(),
                dt.datetime(2000, 1, 1, 1, 0, tzinfo=dt.timezone.utc),
                pytest.raises(AleBenchError, match=r"The session is finished\."),
                id="ng_session_duration",
            ),
            pytest.param(
                ResourceUsage(num_call_private_eval=1),
                dt.datetime(2000, 1, 1, 0, 30, tzinfo=dt.timezone.utc),
                pytest.raises(AleBenchError, match=r"The session is finished\."),
                id="ng_private_eval_called",
            ),
            pytest.param(
                ResourceUsage(num_case_gen=2),
                dt.datetime(2000, 1, 1, 0, 30, tzinfo=dt.timezone.utc),
                does_not_raise(),
                id="ok_maximum",
            ),
            pytest.param(
                ResourceUsage(num_case_gen=3),
                dt.datetime(2000, 1, 1, 0, 30, tzinfo=dt.timezone.utc),
                pytest.raises(
                    AleBenchError,
                    match=r"Exceeded the maximum resource usage for the `case_gen` function after the action\.",
                ),
                id="ng_num_case_gen_after_minimum",
            ),
            pytest.param(
                ResourceUsage(num_case_gen=4),
                dt.datetime(2000, 1, 1, 0, 30, tzinfo=dt.timezone.utc),
                pytest.raises(
                    AleBenchError,
                    match=r"Exceeded the maximum resource usage for the `case_gen` function after the action\.",
                ),
                id="ng_num_case_gen_after_maximum",
            ),
            pytest.param(
                ResourceUsage(num_case_gen=5),
                dt.datetime(2000, 1, 1, 0, 30, tzinfo=dt.timezone.utc),
                pytest.raises(
                    AleBenchError, match=r"Exceeded the maximum resource usage for the `case_gen` function\."
                ),
                id="ng_num_case_gen_before",
            ),
        ],
    )
    def test_case_gen(
        self,
        current_resource_usage: ResourceUsage,
        utc_now: dt.datetime,
        context: AbstractContextManager[None],
        dummy_session: Session,
        mocker: MockerFixture,
    ) -> None:
        dummy_session._session_started_at = dt.datetime(2000, 1, 1, 0, 0, tzinfo=dt.timezone.utc)
        dummy_session._current_resource_usage = current_resource_usage
        mocked_datetime = mocker.patch("ale_bench.session.dt.datetime", return_value=utc_now)
        mocked_datetime.now.return_value = utc_now
        with context:
            dummy_session.case_gen(seed=[0, 1, 2])
            action_log = [json.loads(log) for log in dummy_session.action_log]
            assert len(action_log) == 1
            assert action_log[0]["function"] == "case_gen"
            assert action_log[0]["arguments"] == {"seed": [0, 1, 2], "gen_kwargs": {}}
            assert action_log[0]["elapsed_time"] == pytest.approx(
                (utc_now - dummy_session.session_started_at).total_seconds()
            )

    @pytest.mark.parametrize(
        "current_resource_usage,utc_now,context",
        [
            pytest.param(
                ResourceUsage(), dt.datetime(2000, 1, 1, 0, 30, tzinfo=dt.timezone.utc), does_not_raise(), id="ok"
            ),
            pytest.param(
                ResourceUsage(),
                dt.datetime(2000, 1, 1, 1, 0, tzinfo=dt.timezone.utc),
                pytest.raises(AleBenchError, match=r"The session is finished\."),
                id="ng_session_duration",
            ),
            pytest.param(
                ResourceUsage(num_call_private_eval=1),
                dt.datetime(2000, 1, 1, 0, 30, tzinfo=dt.timezone.utc),
                pytest.raises(AleBenchError, match=r"The session is finished\."),
                id="ng_private_eval_called",
            ),
            pytest.param(
                ResourceUsage(num_case_eval=2, execution_time_case_eval=45.6),
                dt.datetime(2000, 1, 1, 0, 30, tzinfo=dt.timezone.utc),
                does_not_raise(),
                id="ok_maximum",
            ),
            pytest.param(
                ResourceUsage(num_case_eval=3, execution_time_case_eval=45.6),
                dt.datetime(2000, 1, 1, 0, 30, tzinfo=dt.timezone.utc),
                pytest.raises(
                    AleBenchError,
                    match=r"Exceeded the maximum resource usage for the `case_eval` function after the action\.",
                ),
                id="ng_num_case_eval_after_minimum",
            ),
            pytest.param(
                ResourceUsage(num_case_eval=4, execution_time_case_eval=45.6),
                dt.datetime(2000, 1, 1, 0, 30, tzinfo=dt.timezone.utc),
                pytest.raises(
                    AleBenchError,
                    match=r"Exceeded the maximum resource usage for the `case_eval` function after the action\.",
                ),
                id="ng_num_case_eval_after_maximum",
            ),
            pytest.param(
                ResourceUsage(num_case_eval=5, execution_time_case_eval=45.6),
                dt.datetime(2000, 1, 1, 0, 30, tzinfo=dt.timezone.utc),
                pytest.raises(
                    AleBenchError, match=r"Exceeded the maximum resource usage for the `case_eval` function\."
                ),
                id="ng_num_case_eval_before",
            ),
            pytest.param(
                ResourceUsage(num_case_eval=2, execution_time_case_eval=45.7),
                dt.datetime(2000, 1, 1, 0, 30, tzinfo=dt.timezone.utc),
                pytest.raises(
                    AleBenchError,
                    match=r"Exceeded the maximum resource usage for the `case_eval` function after the action\.",
                ),
                id="ng_execution_time_case_eval_after_minimum",
            ),
            pytest.param(
                ResourceUsage(num_case_eval=2, execution_time_case_eval=59.9),
                dt.datetime(2000, 1, 1, 0, 30, tzinfo=dt.timezone.utc),
                pytest.raises(
                    AleBenchError,
                    match=r"Exceeded the maximum resource usage for the `case_eval` function after the action\.",
                ),
                id="ng_execution_time_case_eval_after_maximum",
            ),
            pytest.param(
                ResourceUsage(num_case_eval=2, execution_time_case_eval=60.0),
                dt.datetime(2000, 1, 1, 0, 30, tzinfo=dt.timezone.utc),
                pytest.raises(
                    AleBenchError, match=r"Exceeded the maximum resource usage for the `case_eval` function\."
                ),
                id="ng_execution_time_case_eval_before",
            ),
        ],
    )
    def test_case_eval(
        self,
        current_resource_usage: ResourceUsage,
        utc_now: dt.datetime,
        context: AbstractContextManager[None],
        dummy_session: Session,
        mocker: MockerFixture,
    ) -> None:
        dummy_session._session_started_at = dt.datetime(2000, 1, 1, 0, 0, tzinfo=dt.timezone.utc)
        dummy_session._current_resource_usage = current_resource_usage
        mocked_datetime = mocker.patch("ale_bench.session.dt.datetime", return_value=utc_now)
        mocked_datetime.now.return_value = utc_now
        with context:
            dummy_session.case_eval(
                input_str=["dummy input 1", "dummy input 2", "dummy input 3"], code="dummy code", code_language="rust"
            )
            action_log = [json.loads(log) for log in dummy_session.action_log]
            assert len(action_log) == 1
            assert action_log[0]["function"] == "case_eval"
            assert action_log[0]["arguments"] == {
                "input_str": ["dummy input 1", "dummy input 2", "dummy input 3"],
                "code": "dummy code",
                "code_language": "rust",
                "judge_version": "202301",
                "time_limit": 5.0,
                "memory_limit": 1073741824,
            }
            assert action_log[0]["elapsed_time"] == pytest.approx(
                (utc_now - dummy_session.session_started_at).total_seconds()
            )

    @pytest.mark.parametrize(
        "current_resource_usage,utc_now,context",
        [
            pytest.param(
                ResourceUsage(), dt.datetime(2000, 1, 1, 0, 30, tzinfo=dt.timezone.utc), does_not_raise(), id="ok"
            ),
            pytest.param(
                ResourceUsage(),
                dt.datetime(2000, 1, 1, 1, 0, tzinfo=dt.timezone.utc),
                pytest.raises(AleBenchError, match=r"The session is finished\."),
                id="ng_session_duration",
            ),
            pytest.param(
                ResourceUsage(num_call_private_eval=1),
                dt.datetime(2000, 1, 1, 0, 30, tzinfo=dt.timezone.utc),
                pytest.raises(AleBenchError, match=r"The session is finished\."),
                id="ng_private_eval_called",
            ),
            pytest.param(
                ResourceUsage(num_case_gen=2, num_case_eval=2, execution_time_case_eval=45.6),
                dt.datetime(2000, 1, 1, 0, 30, tzinfo=dt.timezone.utc),
                does_not_raise(),
                id="ok_maximum",
            ),
            pytest.param(
                ResourceUsage(num_case_gen=3, num_case_eval=2, execution_time_case_eval=45.6),
                dt.datetime(2000, 1, 1, 0, 30, tzinfo=dt.timezone.utc),
                pytest.raises(
                    AleBenchError,
                    match=r"Exceeded the maximum resource usage for the `case_gen` function after the action\.",
                ),
                id="ng_num_case_gen_after_minimum",
            ),
            pytest.param(
                ResourceUsage(num_case_gen=4, num_case_eval=2, execution_time_case_eval=45.6),
                dt.datetime(2000, 1, 1, 0, 30, tzinfo=dt.timezone.utc),
                pytest.raises(
                    AleBenchError,
                    match=r"Exceeded the maximum resource usage for the `case_gen` function after the action\.",
                ),
                id="ng_num_case_gen_after_maximum",
            ),
            pytest.param(
                ResourceUsage(num_case_gen=5, num_case_eval=2, execution_time_case_eval=45.6),
                dt.datetime(2000, 1, 1, 0, 30, tzinfo=dt.timezone.utc),
                pytest.raises(
                    AleBenchError, match=r"Exceeded the maximum resource usage for the `case_gen_eval` function\."
                ),
                id="ng_num_case_gen_before",
            ),
            pytest.param(
                ResourceUsage(num_case_gen=2, num_case_eval=3, execution_time_case_eval=45.6),
                dt.datetime(2000, 1, 1, 0, 30, tzinfo=dt.timezone.utc),
                pytest.raises(
                    AleBenchError,
                    match=r"Exceeded the maximum resource usage for the `case_eval` function after the action\.",
                ),
                id="ng_num_case_eval_after_minimum",
            ),
            pytest.param(
                ResourceUsage(num_case_gen=2, num_case_eval=4, execution_time_case_eval=45.6),
                dt.datetime(2000, 1, 1, 0, 30, tzinfo=dt.timezone.utc),
                pytest.raises(
                    AleBenchError,
                    match=r"Exceeded the maximum resource usage for the `case_eval` function after the action\.",
                ),
                id="ng_num_case_eval_after_maximum",
            ),
            pytest.param(
                ResourceUsage(num_case_gen=2, num_case_eval=5, execution_time_case_eval=45.6),
                dt.datetime(2000, 1, 1, 0, 30, tzinfo=dt.timezone.utc),
                pytest.raises(
                    AleBenchError, match=r"Exceeded the maximum resource usage for the `case_gen_eval` function\."
                ),
                id="ng_num_case_eval_before",
            ),
            pytest.param(
                ResourceUsage(num_case_gen=2, num_case_eval=2, execution_time_case_eval=45.7),
                dt.datetime(2000, 1, 1, 0, 30, tzinfo=dt.timezone.utc),
                pytest.raises(
                    AleBenchError,
                    match=r"Exceeded the maximum resource usage for the `case_eval` function after the action\.",
                ),
                id="ng_execution_time_case_eval_after_minimum",
            ),
            pytest.param(
                ResourceUsage(num_case_gen=2, num_case_eval=2, execution_time_case_eval=59.9),
                dt.datetime(2000, 1, 1, 0, 30, tzinfo=dt.timezone.utc),
                pytest.raises(
                    AleBenchError,
                    match=r"Exceeded the maximum resource usage for the `case_eval` function after the action\.",
                ),
                id="ng_execution_time_case_eval_after_maximum",
            ),
            pytest.param(
                ResourceUsage(num_case_gen=2, num_case_eval=2, execution_time_case_eval=60.0),
                dt.datetime(2000, 1, 1, 0, 30, tzinfo=dt.timezone.utc),
                pytest.raises(
                    AleBenchError, match=r"Exceeded the maximum resource usage for the `case_gen_eval` function\."
                ),
                id="ng_execution_time_case_eval_before",
            ),
        ],
    )
    def test_case_gen_eval(
        self,
        current_resource_usage: ResourceUsage,
        utc_now: dt.datetime,
        context: AbstractContextManager[None],
        dummy_session: Session,
        mocker: MockerFixture,
    ) -> None:
        dummy_session._session_started_at = dt.datetime(2000, 1, 1, 0, 0, tzinfo=dt.timezone.utc)
        dummy_session._current_resource_usage = current_resource_usage
        mocked_datetime = mocker.patch("ale_bench.session.dt.datetime", return_value=utc_now)
        mocked_datetime.now.return_value = utc_now
        with context:
            dummy_session.case_gen_eval(code="dummy code", code_language="rust", seed=[0, 1, 2])
            action_log = [json.loads(log) for log in dummy_session.action_log]
            assert len(action_log) == 2
            assert action_log[0]["function"] == "case_gen"
            assert action_log[0]["arguments"] == {"seed": [0, 1, 2], "gen_kwargs": {}}
            assert action_log[0]["elapsed_time"] == pytest.approx(
                (utc_now - dummy_session.session_started_at).total_seconds()
            )
            assert action_log[1]["function"] == "case_eval"
            assert action_log[1]["arguments"] == {
                "input_str": ["dummy input 1", "dummy input 2", "dummy input 3"],
                "code": "dummy code",
                "code_language": "rust",
                "judge_version": "202301",
                "time_limit": 5.0,
                "memory_limit": 1073741824,
            }
            assert action_log[1]["elapsed_time"] == pytest.approx(
                (utc_now - dummy_session.session_started_at).total_seconds()
            )

    @pytest.mark.parametrize(
        "utc_now,context",
        [
            pytest.param(dt.datetime(2000, 1, 1, 0, 30, tzinfo=dt.timezone.utc), does_not_raise(), id="ok"),
            pytest.param(
                dt.datetime(2000, 1, 1, 1, 0, tzinfo=dt.timezone.utc),
                pytest.raises(AleBenchError, match=r"The session is finished\."),
                id="ng_session_duration",
            ),
        ],
    )
    def test_local_visualization(
        self,
        utc_now: dt.datetime,
        context: AbstractContextManager[None],
        dummy_session: Session,
        mocker: MockerFixture,
    ) -> None:
        dummy_session._session_started_at = dt.datetime(2000, 1, 1, 0, 0, tzinfo=dt.timezone.utc)
        mocked_datetime = mocker.patch("ale_bench.session.dt.datetime", return_value=utc_now)
        mocked_datetime.now.return_value = utc_now
        with context:
            dummy_session.local_visualization(input_str="dummy input", output_str="dummy output")
            action_log = [json.loads(log) for log in dummy_session.action_log]
            assert len(action_log) == 1
            assert action_log[0]["function"] == "local_visualization"
            assert action_log[0]["arguments"] == {"input_str": ["dummy input"], "output_str": ["dummy output"]}
            assert action_log[0]["elapsed_time"] == pytest.approx(
                (utc_now - dummy_session.session_started_at).total_seconds()
            )

    @pytest.mark.parametrize(
        "current_resource_usage,utc_now,context",
        [
            pytest.param(
                ResourceUsage(), dt.datetime(2000, 1, 1, 0, 30, tzinfo=dt.timezone.utc), does_not_raise(), id="ok"
            ),
            pytest.param(
                ResourceUsage(),
                dt.datetime(2000, 1, 1, 0, 29, 59, tzinfo=dt.timezone.utc),
                pytest.raises(AleBenchError, match=r"The next public evaluation is not allowed yet\."),
                id="ng_before_next_public_eval",
            ),
            pytest.param(
                ResourceUsage(),
                dt.datetime(2000, 1, 1, 1, 0, tzinfo=dt.timezone.utc),
                pytest.raises(AleBenchError, match=r"The session is finished\."),
                id="ng_session_duration",
            ),
            pytest.param(
                ResourceUsage(num_call_private_eval=1),
                dt.datetime(2000, 1, 1, 0, 30, tzinfo=dt.timezone.utc),
                pytest.raises(AleBenchError, match=r"The session is finished\."),
                id="ng_private_eval_called",
            ),
            pytest.param(
                ResourceUsage(num_call_public_eval=2),
                dt.datetime(2000, 1, 1, 0, 30, tzinfo=dt.timezone.utc),
                does_not_raise(),
                id="ok_maximum",
            ),
            pytest.param(
                ResourceUsage(num_call_public_eval=3),
                dt.datetime(2000, 1, 1, 0, 30, tzinfo=dt.timezone.utc),
                pytest.raises(
                    AleBenchError, match=r"Exceeded the maximum resource usage for the `public_eval` function\."
                ),
                id="ng_num_call_public_eval_before",
            ),
        ],
    )
    def test_public_eval(
        self,
        current_resource_usage: ResourceUsage,
        utc_now: dt.datetime,
        context: AbstractContextManager[None],
        dummy_session: Session,
        mocker: MockerFixture,
    ) -> None:
        dummy_session._session_started_at = dt.datetime(2000, 1, 1, 0, 0, tzinfo=dt.timezone.utc)
        dummy_session._last_public_eval_time = dt.datetime(2000, 1, 1, 0, 0, 0, tzinfo=dt.timezone.utc)
        dummy_session._current_resource_usage = current_resource_usage
        mocked_datetime = mocker.patch("ale_bench.session.dt.datetime", return_value=utc_now)
        mocked_datetime.now.return_value = utc_now
        with context:
            dummy_session.public_eval(code="dummy code", code_language="rust")
            action_log = [json.loads(log) for log in dummy_session.action_log]
            assert len(action_log) == 1
            assert action_log[0]["function"] == "public_eval"
            assert action_log[0]["arguments"] == {
                "code": "dummy code",
                "code_language": "rust",
                "judge_version": "202301",
            }
            assert action_log[0]["elapsed_time"] == pytest.approx(
                (utc_now - dummy_session.session_started_at).total_seconds()
            )

    @pytest.mark.parametrize(
        "current_resource_usage,utc_now,context",
        [
            pytest.param(
                ResourceUsage(), dt.datetime(2000, 1, 1, 0, 30, tzinfo=dt.timezone.utc), does_not_raise(), id="ok"
            ),
            pytest.param(
                ResourceUsage(),
                dt.datetime(2000, 1, 1, 1, 0, tzinfo=dt.timezone.utc),
                pytest.raises(AleBenchError, match=r"The session is finished\."),
                id="ng_session_duration",
            ),
            pytest.param(
                ResourceUsage(num_call_private_eval=1),
                dt.datetime(2000, 1, 1, 0, 30, tzinfo=dt.timezone.utc),
                pytest.raises(AleBenchError, match=r"The session is finished\."),
                id="ng_private_eval_called",
            ),
        ],
    )
    def test_private_eval(
        self,
        current_resource_usage: ResourceUsage,
        utc_now: dt.datetime,
        context: AbstractContextManager[None],
        dummy_session: Session,
        mocker: MockerFixture,
    ) -> None:
        dummy_session._session_started_at = dt.datetime(2000, 1, 1, 0, 0, tzinfo=dt.timezone.utc)
        dummy_session._current_resource_usage = current_resource_usage
        mocked_datetime = mocker.patch("ale_bench.session.dt.datetime", return_value=utc_now)
        mocked_datetime.now.return_value = utc_now
        with context:
            dummy_session.private_eval(code="dummy code", code_language="rust")
            action_log = [json.loads(log) for log in dummy_session.action_log]
            assert len(action_log) == 1
            assert action_log[0]["function"] == "private_eval"
            assert action_log[0]["arguments"] == {
                "code": "dummy code",
                "code_language": "rust",
                "judge_version": "202301",
            }
            assert action_log[0]["elapsed_time"] == pytest.approx(
                (utc_now - dummy_session.session_started_at).total_seconds()
            )

    def test_save(self, dummy_session: Session) -> None:
        # Case evaluation x 1 (3 cases), Public evaluation x 1
        dummy_session.case_eval(
            input_str=["dummy input 1", "dummy input 2", "dummy input 3"], code="dummy code", code_language="rust"
        )
        dummy_session.public_eval(code="dummy code", code_language="rust")
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir) / "dummy_session.json"
            dummy_session.save(tmp_path)
            assert tmp_path.is_file()
            actual = json.load(tmp_path.open())
            assert actual["problem_id"] == "ahc001"
            assert actual["public_seeds"] == [0, 1, 2]
            assert actual["private_seeds"] == [3, 4, 5]
            assert actual["use_same_time_scale"] is True
            assert actual["maximum_resource_usage"]["num_case_gen"] == 5
            assert actual["maximum_resource_usage"]["num_case_eval"] == 5
            assert actual["maximum_resource_usage"]["execution_time_case_eval"] == 60.0
            assert actual["maximum_resource_usage"]["num_call_public_eval"] == 3
            assert actual["maximum_resource_usage"]["num_call_private_eval"] == 1
            assert actual["session_duration"] == 3600.0
            assert actual["visualization_server_port"] is None
            assert actual["num_workers"] == 1
            assert actual["current_resource_usage"]["num_case_gen"] == 0
            assert actual["current_resource_usage"]["num_case_eval"] == 3
            assert actual["current_resource_usage"]["execution_time_case_eval"] == pytest.approx(14.4)
            assert actual["current_resource_usage"]["num_call_public_eval"] == 1
            assert actual["current_resource_usage"]["num_call_private_eval"] == 0
            action_log = [json.loads(log) for log in actual["action_log"]]
            assert len(action_log) == 2
            assert action_log[0]["function"] == "case_eval"
            assert action_log[0]["arguments"] == {
                "input_str": ["dummy input 1", "dummy input 2", "dummy input 3"],
                "code": "dummy code",
                "code_language": "rust",
                "judge_version": "202301",
                "time_limit": 5.0,
                "memory_limit": 1073741824,
            }
            assert isinstance(action_log[0]["elapsed_time"], float)
            assert action_log[1]["function"] == "public_eval"
            assert action_log[1]["arguments"] == {
                "code": "dummy code",
                "code_language": "rust",
                "judge_version": "202301",
            }
            assert isinstance(action_log[1]["elapsed_time"], float)
            assert actual["last_public_eval_time"] == dummy_session.last_public_eval_time.timestamp()
            assert actual["last_private_eval_time"] == 0.0
            assert actual["session_started_at"] == dummy_session.session_started_at.timestamp()
            assert (
                dummy_session.last_public_eval_time.timestamp()
                < actual["session_paused_at"]
                < dummy_session.last_public_eval_time.timestamp() + 10.0
            )  # NOTE: We check the range of the timestamp because actual paused time cannot be determined

    def test_problem(self, dummy_session: Session) -> None:
        assert dummy_session.problem.statement == "dummy statement"

    def test_problem_id(self, dummy_session: Session) -> None:
        assert dummy_session.problem_id == "ahc001"

    def test_lite_version(self, dummy_session: Session) -> None:
        assert dummy_session.lite_version is False

    def test_public_seeds(self, dummy_session: Session) -> None:
        assert dummy_session.public_seeds == [0, 1, 2]

    def test_num_public_cases(self, dummy_session: Session) -> None:
        assert dummy_session.num_public_cases == 3

    def test_private_seeds(self, dummy_session: Session) -> None:
        with pytest.raises(AleBenchError, match=r"Accessing private seeds is not allowed\."):
            dummy_session.private_seeds

    def test_num_private_cases(self, dummy_session: Session) -> None:
        assert dummy_session.num_private_cases == 3

    def test_standings(self, dummy_session: Session) -> None:
        with pytest.raises(AleBenchError, match=r"Accessing standings is not allowed\."):
            dummy_session.standings

    def test_rank_performance_map(self, dummy_session: Session) -> None:
        with pytest.raises(AleBenchError, match=r"Accessing rank performance map is not allowed\."):
            dummy_session.rank_performance_map

    def test_tool_dir(self, dummy_session: Session) -> None:
        assert dummy_session.tool_dir == Path("/tmp/dummy")

    def test_rust_src_dir(self, dummy_session: Session) -> None:
        assert dummy_session.rust_src_dir == Path("/tmp/dummy/tools/src")

    def test_use_same_time_scale(self, dummy_session: Session) -> None:
        assert dummy_session.use_same_time_scale is True

    def test_maximum_resource_usage(self, dummy_session: Session) -> None:
        assert dummy_session.maximum_resource_usage.num_case_gen == 5
        assert dummy_session.maximum_resource_usage.num_case_eval == 5
        assert dummy_session.maximum_resource_usage.execution_time_case_eval == 60.0
        assert dummy_session.maximum_resource_usage.num_call_public_eval == 3
        assert dummy_session.maximum_resource_usage.num_call_private_eval == 1

    def test_current_resource_usage(self, dummy_session: Session) -> None:
        assert dummy_session.current_resource_usage.num_case_gen == 0
        assert dummy_session.current_resource_usage.num_case_eval == 0
        assert dummy_session.current_resource_usage.execution_time_case_eval == 0.0
        assert dummy_session.current_resource_usage.num_call_public_eval == 0
        assert dummy_session.current_resource_usage.num_call_private_eval == 0
        # Case evaluation x 1 (3 cases), Public evaluation x 2
        dummy_session.case_eval(
            input_str=["dummy input 1", "dummy input 2", "dummy input 3"], code="dummy code", code_language="rust"
        )
        for _ in range(2):
            dummy_session.public_eval(code="dummy code", code_language="rust")
            dummy_session._last_public_eval_time = dt.datetime.fromtimestamp(0, tz=dt.timezone.utc)
        assert dummy_session.current_resource_usage.num_case_gen == 0
        assert dummy_session.current_resource_usage.num_case_eval == 3
        assert dummy_session.current_resource_usage.execution_time_case_eval == pytest.approx(14.4)
        assert dummy_session.current_resource_usage.num_call_public_eval == 2
        assert dummy_session.current_resource_usage.num_call_private_eval == 0

    def test_remaining_resource_usage(self, dummy_session: Session) -> None:
        assert dummy_session.remaining_resource_usage.num_case_gen == 5
        assert dummy_session.remaining_resource_usage.num_case_eval == 5
        assert dummy_session.remaining_resource_usage.execution_time_case_eval == 60.0
        assert dummy_session.remaining_resource_usage.num_call_public_eval == 3
        assert dummy_session.remaining_resource_usage.num_call_private_eval == 1
        # Case generation & evaluation x 1 (3 cases), Public evaluation x 2
        dummy_session.case_gen_eval(seed=[0, 1, 2], code="dummy code", code_language="rust")
        for _ in range(2):
            dummy_session.public_eval(code="dummy code", code_language="rust")
            dummy_session._last_public_eval_time = dt.datetime.fromtimestamp(0, tz=dt.timezone.utc)
        assert dummy_session.remaining_resource_usage.num_case_gen == 2
        assert dummy_session.remaining_resource_usage.num_case_eval == 2
        assert dummy_session.remaining_resource_usage.execution_time_case_eval == pytest.approx(45.6)
        assert dummy_session.remaining_resource_usage.num_call_public_eval == 1
        assert dummy_session.remaining_resource_usage.num_call_private_eval == 1

    def test_action_log(self, dummy_session: Session) -> None:
        assert isinstance(dummy_session.action_log, list)
        assert len(dummy_session.action_log) == 0
        # Case generation & evaluation x 1 (3 cases), Public evaluation x 2
        dummy_session.case_gen_eval(seed=[0, 1, 2], code="dummy code", code_language="rust")
        for _ in range(2):
            dummy_session.public_eval(code="dummy code", code_language="rust")
            dummy_session._last_public_eval_time = dt.datetime.fromtimestamp(0, tz=dt.timezone.utc)
        action_log = [json.loads(log) for log in dummy_session.action_log]
        assert len(action_log) == 4
        assert action_log[0]["function"] == "case_gen"
        assert action_log[0]["arguments"] == {"seed": [0, 1, 2], "gen_kwargs": {}}
        assert isinstance(action_log[0]["elapsed_time"], float)
        assert action_log[1]["function"] == "case_eval"
        assert action_log[1]["arguments"] == {
            "input_str": ["dummy input 1", "dummy input 2", "dummy input 3"],
            "code": "dummy code",
            "code_language": "rust",
            "judge_version": "202301",
            "time_limit": 5.0,
            "memory_limit": 1073741824,
        }
        assert isinstance(action_log[1]["elapsed_time"], float)
        assert action_log[2]["function"] == "public_eval"
        assert action_log[2]["arguments"] == {"code": "dummy code", "code_language": "rust", "judge_version": "202301"}
        assert isinstance(action_log[2]["elapsed_time"], float)
        assert action_log[3]["function"] == "public_eval"
        assert action_log[3]["arguments"] == {"code": "dummy code", "code_language": "rust", "judge_version": "202301"}
        assert isinstance(action_log[3]["elapsed_time"], float)

    def test_last_public_eval_time(self, dummy_session: Session) -> None:
        assert dummy_session.last_public_eval_time == dt.datetime(1970, 1, 1, 0, 0, tzinfo=dt.timezone.utc)

    def next_public_eval_time(self, dummy_session: Session) -> None:
        assert dummy_session.next_public_eval_time == dt.datetime(1970, 1, 1, 0, 30, tzinfo=dt.timezone.utc)

    def test_last_private_eval_time(self, dummy_session: Session) -> None:
        assert dummy_session.last_private_eval_time == dt.datetime(1970, 1, 1, 0, 0, tzinfo=dt.timezone.utc)

    def test_session_duration(self, dummy_session: Session) -> None:
        assert dummy_session.session_duration == dt.timedelta(hours=1)

    def test_session_started_at(self, dummy_session: Session) -> None:
        dummy_session._session_started_at = dt.datetime(2000, 1, 1, 0, 0, tzinfo=dt.timezone.utc)
        assert dummy_session.session_started_at == dt.datetime(2000, 1, 1, 0, 0, tzinfo=dt.timezone.utc)

    @pytest.mark.parametrize(
        "utc_now,expected",
        [
            pytest.param(
                dt.datetime(1999, 12, 31, 23, 59, tzinfo=dt.timezone.utc),
                dt.timedelta(seconds=3660),
                id="session_not_started",
            ),
            pytest.param(
                dt.datetime(2000, 1, 1, 0, 0, tzinfo=dt.timezone.utc),
                dt.timedelta(seconds=3600),
                id="session_just_started",
            ),
            pytest.param(
                dt.datetime(2000, 1, 1, 0, 30, tzinfo=dt.timezone.utc), dt.timedelta(seconds=1800), id="session_middle"
            ),
            pytest.param(
                dt.datetime(2000, 1, 1, 0, 59, 59, tzinfo=dt.timezone.utc),
                dt.timedelta(seconds=1),
                id="session_almost_finished",
            ),
            pytest.param(
                dt.datetime(2000, 1, 1, 1, 0, tzinfo=dt.timezone.utc), dt.timedelta(seconds=0), id="session_finished"
            ),
            pytest.param(
                dt.datetime(2000, 1, 1, 1, 0, 1, tzinfo=dt.timezone.utc),
                dt.timedelta(seconds=-1),
                id="session_finished_over",
            ),
        ],
    )
    def test_session_remaining_time(
        self,
        utc_now: dt.datetime,
        expected: dt.timedelta,
        dummy_session: Session,
        mocker: MockerFixture,
    ) -> None:
        dummy_session._session_started_at = dt.datetime(2000, 1, 1, 0, 0, tzinfo=dt.timezone.utc)
        mocked_datetime = mocker.patch("ale_bench.session.dt.datetime", return_value=utc_now)
        mocked_datetime.now.return_value = utc_now
        assert dummy_session.session_remaining_time == expected

    @pytest.mark.parametrize(
        "utc_now,context",
        [
            pytest.param(
                dt.datetime(1999, 12, 31, 23, 59, tzinfo=dt.timezone.utc), does_not_raise(), id="session_not_started"
            ),
            pytest.param(
                dt.datetime(2000, 1, 1, 0, 0, tzinfo=dt.timezone.utc), does_not_raise(), id="session_just_started"
            ),
            pytest.param(dt.datetime(2000, 1, 1, 0, 30, tzinfo=dt.timezone.utc), does_not_raise(), id="session_middle"),
            pytest.param(
                dt.datetime(2000, 1, 1, 0, 59, 59, tzinfo=dt.timezone.utc),
                does_not_raise(),
                id="session_almost_finished",
            ),
            pytest.param(
                dt.datetime(2000, 1, 1, 1, 0, tzinfo=dt.timezone.utc),
                pytest.raises(AleBenchError, match=r"The session has already finished\."),
                id="session_finished",
            ),
            pytest.param(
                dt.datetime(2000, 1, 1, 1, 0, 1, tzinfo=dt.timezone.utc),
                pytest.raises(AleBenchError, match=r"The session has already finished\."),
                id="session_finished_over",
            ),
        ],
    )
    def test_session_finished(
        self,
        utc_now: dt.datetime,
        context: AbstractContextManager[None],
        dummy_session: Session,
        mocker: MockerFixture,
    ) -> None:
        dummy_session._session_started_at = dt.datetime(2000, 1, 1, 0, 0, tzinfo=dt.timezone.utc)
        mocked_datetime = mocker.patch("ale_bench.session.dt.datetime", return_value=utc_now)
        mocked_datetime.now.return_value = utc_now
        with context:
            assert dummy_session.session_finished is False

    def test_session_finished_after_private_eval(self, dummy_session: Session) -> None:
        assert dummy_session.session_finished is False
        # Private Evaluation
        dummy_session.private_eval(code="dummy code", code_language="rust")
        with pytest.raises(
            AleBenchError, match=r"Exceeded the maximum resource usage for the `private_eval` function\."
        ):
            dummy_session.session_finished

    @pytest.mark.parametrize(
        "function_type,current_resource_usage,utc_now,context",
        [
            pytest.param(
                AleBenchFunction.CASE_GEN,
                ResourceUsage(
                    num_case_gen=4,
                    num_case_eval=5,
                    execution_time_case_eval=60.0,
                    num_call_public_eval=3,
                    num_call_private_eval=1,
                ),
                dt.datetime(2000, 1, 1, 0, 59, 59, tzinfo=dt.timezone.utc),
                does_not_raise(),
                id="case_gen_ok",
            ),
            pytest.param(
                AleBenchFunction.CASE_GEN,
                ResourceUsage(
                    num_case_gen=4,
                    num_case_eval=5,
                    execution_time_case_eval=60.0,
                    num_call_public_eval=3,
                    num_call_private_eval=1,
                ),
                dt.datetime(2000, 1, 1, 1, 0, 0, tzinfo=dt.timezone.utc),
                pytest.raises(AleBenchError, match=r"The session has already finished\."),
                id="case_gen_ng_session_duration",
            ),
            pytest.param(
                AleBenchFunction.CASE_GEN,
                ResourceUsage(
                    num_case_gen=5,
                    num_case_eval=5,
                    execution_time_case_eval=60.0,
                    num_call_public_eval=3,
                    num_call_private_eval=1,
                ),
                dt.datetime(2000, 1, 1, 0, 59, 59, tzinfo=dt.timezone.utc),
                pytest.raises(
                    AleBenchError, match=r"Exceeded the maximum resource usage for the `case_gen` function\."
                ),
                id="case_gen_ng_num_case_gen",
            ),
            pytest.param(
                AleBenchFunction.CASE_EVAL,
                ResourceUsage(
                    num_case_gen=5,
                    num_case_eval=4,
                    execution_time_case_eval=59.9,
                    num_call_public_eval=3,
                    num_call_private_eval=1,
                ),
                dt.datetime(2000, 1, 1, 0, 59, 59, tzinfo=dt.timezone.utc),
                does_not_raise(),
                id="case_eval_ok",
            ),
            pytest.param(
                AleBenchFunction.CASE_EVAL,
                ResourceUsage(
                    num_case_gen=5,
                    num_case_eval=4,
                    execution_time_case_eval=59.9,
                    num_call_public_eval=3,
                    num_call_private_eval=1,
                ),
                dt.datetime(2000, 1, 1, 1, 0, 0, tzinfo=dt.timezone.utc),
                pytest.raises(AleBenchError, match=r"The session has already finished\."),
                id="case_eval_ng_session_duration",
            ),
            pytest.param(
                AleBenchFunction.CASE_EVAL,
                ResourceUsage(
                    num_case_gen=5,
                    num_case_eval=5,
                    execution_time_case_eval=59.9,
                    num_call_public_eval=3,
                    num_call_private_eval=1,
                ),
                dt.datetime(2000, 1, 1, 0, 59, 59, tzinfo=dt.timezone.utc),
                pytest.raises(
                    AleBenchError, match=r"Exceeded the maximum resource usage for the `case_eval` function\."
                ),
                id="case_eval_ng_num_case_eval",
            ),
            pytest.param(
                AleBenchFunction.CASE_EVAL,
                ResourceUsage(
                    num_case_gen=5,
                    num_case_eval=4,
                    execution_time_case_eval=60.0,
                    num_call_public_eval=3,
                    num_call_private_eval=1,
                ),
                dt.datetime(2000, 1, 1, 0, 59, 59, tzinfo=dt.timezone.utc),
                pytest.raises(
                    AleBenchError, match=r"Exceeded the maximum resource usage for the `case_eval` function\."
                ),
                id="case_eval_ng_execution_time_case_eval",
            ),
            pytest.param(
                AleBenchFunction.CASE_GEN_EVAL,
                ResourceUsage(
                    num_case_gen=4,
                    num_case_eval=4,
                    execution_time_case_eval=59.9,
                    num_call_public_eval=3,
                    num_call_private_eval=1,
                ),
                dt.datetime(2000, 1, 1, 0, 59, 59, tzinfo=dt.timezone.utc),
                does_not_raise(),
                id="case_gen_eval_ok",
            ),
            pytest.param(
                AleBenchFunction.CASE_GEN_EVAL,
                ResourceUsage(
                    num_case_gen=4,
                    num_case_eval=4,
                    execution_time_case_eval=59.9,
                    num_call_public_eval=3,
                    num_call_private_eval=1,
                ),
                dt.datetime(2000, 1, 1, 1, 0, 0, tzinfo=dt.timezone.utc),
                pytest.raises(AleBenchError, match=r"The session has already finished\."),
                id="case_gen_eval_ng_session_duration",
            ),
            pytest.param(
                AleBenchFunction.CASE_GEN_EVAL,
                ResourceUsage(
                    num_case_gen=5,
                    num_case_eval=4,
                    execution_time_case_eval=59.9,
                    num_call_public_eval=3,
                    num_call_private_eval=1,
                ),
                dt.datetime(2000, 1, 1, 0, 59, 59, tzinfo=dt.timezone.utc),
                pytest.raises(
                    AleBenchError, match=r"Exceeded the maximum resource usage for the `case_gen_eval` function\."
                ),
                id="case_gen_eval_ng_num_case_gen",
            ),
            pytest.param(
                AleBenchFunction.CASE_GEN_EVAL,
                ResourceUsage(
                    num_case_gen=4,
                    num_case_eval=5,
                    execution_time_case_eval=59.9,
                    num_call_public_eval=3,
                    num_call_private_eval=1,
                ),
                dt.datetime(2000, 1, 1, 0, 59, 59, tzinfo=dt.timezone.utc),
                pytest.raises(
                    AleBenchError, match=r"Exceeded the maximum resource usage for the `case_gen_eval` function\."
                ),
                id="case_gen_eval_ng_num_case_eval",
            ),
            pytest.param(
                AleBenchFunction.CASE_GEN_EVAL,
                ResourceUsage(
                    num_case_gen=4,
                    num_case_eval=4,
                    execution_time_case_eval=60.0,
                    num_call_public_eval=3,
                    num_call_private_eval=1,
                ),
                dt.datetime(2000, 1, 1, 0, 59, 59, tzinfo=dt.timezone.utc),
                pytest.raises(
                    AleBenchError, match=r"Exceeded the maximum resource usage for the `case_gen_eval` function\."
                ),
                id="case_gen_eval_ng_execution_time_case_eval",
            ),
            pytest.param(
                AleBenchFunction.PUBLIC_EVAL,
                ResourceUsage(
                    num_case_gen=5,
                    num_case_eval=5,
                    execution_time_case_eval=60.0,
                    num_call_public_eval=2,
                    num_call_private_eval=1,
                ),
                dt.datetime(2000, 1, 1, 0, 59, 59, tzinfo=dt.timezone.utc),
                does_not_raise(),
                id="public_eval_ok",
            ),
            pytest.param(
                AleBenchFunction.PUBLIC_EVAL,
                ResourceUsage(
                    num_case_gen=5,
                    num_case_eval=5,
                    execution_time_case_eval=60.0,
                    num_call_public_eval=2,
                    num_call_private_eval=1,
                ),
                dt.datetime(2000, 1, 1, 1, 0, 0, tzinfo=dt.timezone.utc),
                pytest.raises(AleBenchError, match=r"The session has already finished\."),
                id="public_eval_ng_session_duration",
            ),
            pytest.param(
                AleBenchFunction.PUBLIC_EVAL,
                ResourceUsage(
                    num_case_gen=5,
                    num_case_eval=5,
                    execution_time_case_eval=60.0,
                    num_call_public_eval=3,
                    num_call_private_eval=1,
                ),
                dt.datetime(2000, 1, 1, 0, 59, 59, tzinfo=dt.timezone.utc),
                pytest.raises(
                    AleBenchError, match=r"Exceeded the maximum resource usage for the `public_eval` function\."
                ),
                id="public_eval_ng_num_call_public_eval",
            ),
            pytest.param(
                AleBenchFunction.PUBLIC_EVAL,
                ResourceUsage(
                    num_case_gen=5,
                    num_case_eval=5,
                    execution_time_case_eval=60.0,
                    num_call_public_eval=2,
                    num_call_private_eval=1,
                ),
                dt.datetime(2000, 1, 1, 0, 59, 58, tzinfo=dt.timezone.utc),
                pytest.raises(AleBenchError, match=r"The next public evaluation is not allowed yet\."),
                id="public_eval_ng_submission_interval",
            ),
            pytest.param(
                AleBenchFunction.PRIVATE_EVAL,
                ResourceUsage(
                    num_case_gen=5,
                    num_case_eval=5,
                    execution_time_case_eval=60.0,
                    num_call_public_eval=3,
                    num_call_private_eval=0,
                ),
                dt.datetime(2000, 1, 1, 0, 59, 59, tzinfo=dt.timezone.utc),
                does_not_raise(),
                id="private_eval_ok",
            ),
            pytest.param(
                AleBenchFunction.PRIVATE_EVAL,
                ResourceUsage(
                    num_case_gen=5,
                    num_case_eval=5,
                    execution_time_case_eval=60.0,
                    num_call_public_eval=3,
                    num_call_private_eval=0,
                ),
                dt.datetime(2000, 1, 1, 1, 0, 0, tzinfo=dt.timezone.utc),
                pytest.raises(AleBenchError, match=r"The session has already finished\."),
                id="private_eval_ng_session_duration",
            ),
            pytest.param(
                AleBenchFunction.PRIVATE_EVAL,
                ResourceUsage(
                    num_case_gen=5,
                    num_case_eval=5,
                    execution_time_case_eval=60.0,
                    num_call_public_eval=3,
                    num_call_private_eval=1,
                ),
                dt.datetime(2000, 1, 1, 0, 59, 59, tzinfo=dt.timezone.utc),
                pytest.raises(
                    AleBenchError, match=r"Exceeded the maximum resource usage for the `private_eval` function\."
                ),
                id="private_eval_ng_num_call_private_eval",
            ),
        ],
    )
    def test_check_within_resource_usage_before(
        self,
        function_type: AleBenchFunction,
        current_resource_usage: ResourceUsage,
        utc_now: dt.datetime,
        context: AbstractContextManager[None],
        dummy_session: Session,
        mocker: MockerFixture,
    ) -> None:
        dummy_session._session_started_at = dt.datetime(2000, 1, 1, 0, 0, tzinfo=dt.timezone.utc)
        dummy_session._last_public_eval_time = dt.datetime(2000, 1, 1, 0, 29, 59, tzinfo=dt.timezone.utc)
        dummy_session._current_resource_usage = current_resource_usage
        mocked_datetime = mocker.patch("ale_bench.session.dt.datetime", return_value=utc_now)
        mocked_datetime.now.return_value = utc_now
        with context:
            assert dummy_session._check_within_resource_usage_before(function_type) is True

    @pytest.mark.parametrize(
        "function_type,current_resource_usage,utc_now,context",
        [
            pytest.param(
                AleBenchFunction.CASE_GEN,
                ResourceUsage(
                    num_case_gen=5,
                    num_case_eval=5,
                    execution_time_case_eval=60.0,
                    num_call_public_eval=3,
                    num_call_private_eval=1,
                ),
                dt.datetime(2000, 1, 1, 1, 0, 1, tzinfo=dt.timezone.utc),
                does_not_raise(),
                id="case_gen_ok",
            ),
            pytest.param(
                AleBenchFunction.CASE_GEN,
                ResourceUsage(
                    num_case_gen=6,
                    num_case_eval=5,
                    execution_time_case_eval=60.0,
                    num_call_public_eval=3,
                    num_call_private_eval=1,
                ),
                dt.datetime(2000, 1, 1, 1, 0, 1, tzinfo=dt.timezone.utc),
                pytest.raises(
                    AleBenchError,
                    match=r"Exceeded the maximum resource usage for the `case_gen` function after the action\.",
                ),
                id="case_gen_ng_num_case_gen",
            ),
            pytest.param(
                AleBenchFunction.CASE_EVAL,
                ResourceUsage(
                    num_case_gen=5,
                    num_case_eval=5,
                    execution_time_case_eval=60.0,
                    num_call_public_eval=3,
                    num_call_private_eval=1,
                ),
                dt.datetime(2000, 1, 1, 1, 0, 1, tzinfo=dt.timezone.utc),
                does_not_raise(),
                id="case_eval_ok",
            ),
            pytest.param(
                AleBenchFunction.CASE_EVAL,
                ResourceUsage(
                    num_case_gen=5,
                    num_case_eval=6,
                    execution_time_case_eval=60.0,
                    num_call_public_eval=3,
                    num_call_private_eval=1,
                ),
                dt.datetime(2000, 1, 1, 1, 0, 1, tzinfo=dt.timezone.utc),
                pytest.raises(
                    AleBenchError,
                    match=r"Exceeded the maximum resource usage for the `case_eval` function after the action\.",
                ),
                id="case_eval_ng_num_case_eval",
            ),
            pytest.param(
                AleBenchFunction.CASE_EVAL,
                ResourceUsage(
                    num_case_gen=5,
                    num_case_eval=5,
                    execution_time_case_eval=60.1,
                    num_call_public_eval=3,
                    num_call_private_eval=1,
                ),
                dt.datetime(2000, 1, 1, 1, 0, 1, tzinfo=dt.timezone.utc),
                pytest.raises(
                    AleBenchError,
                    match=r"Exceeded the maximum resource usage for the `case_eval` function after the action\.",
                ),
                id="case_eval_ng_execution_time_case_eval",
            ),
            pytest.param(
                AleBenchFunction.CASE_GEN_EVAL,
                ResourceUsage(
                    num_case_gen=5,
                    num_case_eval=5,
                    execution_time_case_eval=60.0,
                    num_call_public_eval=3,
                    num_call_private_eval=1,
                ),
                dt.datetime(2000, 1, 1, 1, 0, 1, tzinfo=dt.timezone.utc),
                does_not_raise(),
                id="case_gen_eval_ok",
            ),
            pytest.param(
                AleBenchFunction.CASE_GEN_EVAL,
                ResourceUsage(
                    num_case_gen=6,
                    num_case_eval=5,
                    execution_time_case_eval=60.0,
                    num_call_public_eval=3,
                    num_call_private_eval=1,
                ),
                dt.datetime(2000, 1, 1, 1, 0, 1, tzinfo=dt.timezone.utc),
                pytest.raises(
                    AleBenchError,
                    match=r"Exceeded the maximum resource usage for the `case_gen_eval` function after the action\.",
                ),
                id="case_gen_eval_ng_num_case_gen",
            ),
            pytest.param(
                AleBenchFunction.CASE_GEN_EVAL,
                ResourceUsage(
                    num_case_gen=5,
                    num_case_eval=6,
                    execution_time_case_eval=60.0,
                    num_call_public_eval=3,
                    num_call_private_eval=1,
                ),
                dt.datetime(2000, 1, 1, 1, 0, 1, tzinfo=dt.timezone.utc),
                pytest.raises(
                    AleBenchError,
                    match=r"Exceeded the maximum resource usage for the `case_gen_eval` function after the action\.",
                ),
                id="case_gen_eval_ng_num_case_eval",
            ),
            pytest.param(
                AleBenchFunction.CASE_GEN_EVAL,
                ResourceUsage(
                    num_case_gen=5,
                    num_case_eval=5,
                    execution_time_case_eval=60.1,
                    num_call_public_eval=3,
                    num_call_private_eval=1,
                ),
                dt.datetime(2000, 1, 1, 1, 0, 1, tzinfo=dt.timezone.utc),
                pytest.raises(
                    AleBenchError,
                    match=r"Exceeded the maximum resource usage for the `case_gen_eval` function after the action\.",
                ),
                id="case_gen_eval_ng_execution_time_case_eval",
            ),
            pytest.param(
                AleBenchFunction.PUBLIC_EVAL,
                ResourceUsage(
                    num_case_gen=5,
                    num_case_eval=5,
                    execution_time_case_eval=60.0,
                    num_call_public_eval=3,
                    num_call_private_eval=1,
                ),
                dt.datetime(2000, 1, 1, 1, 0, 1, tzinfo=dt.timezone.utc),
                does_not_raise(),
                id="public_eval_ok",
            ),
            pytest.param(
                AleBenchFunction.PUBLIC_EVAL,
                ResourceUsage(
                    num_case_gen=5,
                    num_case_eval=5,
                    execution_time_case_eval=60.0,
                    num_call_public_eval=4,
                    num_call_private_eval=1,
                ),
                dt.datetime(2000, 1, 1, 1, 0, 1, tzinfo=dt.timezone.utc),
                pytest.raises(
                    AleBenchError,
                    match=r"Exceeded the maximum resource usage for the `public_eval` function after the action\.",
                ),
                id="public_eval_ng_num_call_public_eval",
            ),
            pytest.param(
                AleBenchFunction.PRIVATE_EVAL,
                ResourceUsage(
                    num_case_gen=5,
                    num_case_eval=5,
                    execution_time_case_eval=60.0,
                    num_call_public_eval=3,
                    num_call_private_eval=1,
                ),
                dt.datetime(2000, 1, 1, 1, 0, 1, tzinfo=dt.timezone.utc),
                does_not_raise(),
                id="private_eval_ok",
            ),
            pytest.param(
                AleBenchFunction.PRIVATE_EVAL,
                ResourceUsage(
                    num_case_gen=5,
                    num_case_eval=5,
                    execution_time_case_eval=60.0,
                    num_call_public_eval=3,
                    num_call_private_eval=2,
                ),
                dt.datetime(2000, 1, 1, 1, 0, 1, tzinfo=dt.timezone.utc),
                pytest.raises(
                    AleBenchError,
                    match=r"Exceeded the maximum resource usage for the `private_eval` function after the action\.",
                ),
                id="private_eval_ng_num_call_private_eval",
            ),
        ],
    )
    def test_check_within_resource_usage_after(
        self,
        function_type: AleBenchFunction,
        current_resource_usage: ResourceUsage,
        utc_now: dt.datetime,
        context: AbstractContextManager[None],
        dummy_session: Session,
        mocker: MockerFixture,
    ) -> None:
        dummy_session._session_started_at = dt.datetime(2000, 1, 1, 0, 0, tzinfo=dt.timezone.utc)
        dummy_session._last_public_eval_time = dt.datetime(2000, 1, 1, 0, 29, 59, tzinfo=dt.timezone.utc)
        dummy_session._current_resource_usage = current_resource_usage
        mocked_datetime = mocker.patch("ale_bench.session.dt.datetime", return_value=utc_now)
        mocked_datetime.now.return_value = utc_now
        with context:
            assert dummy_session._check_within_resource_usage_after(function_type) is True

    @pytest.mark.parametrize(
        "seed,gen_kwargs,expected,context",
        [
            pytest.param(None, None, ([0], {}), does_not_raise(), id="default"),
            pytest.param(0, {}, ([0], {}), does_not_raise(), id="ok_scalar"),
            pytest.param([0], {}, ([0], {}), does_not_raise(), id="ok_list"),
            pytest.param([0, 1, 2], {}, ([0, 1, 2], {}), does_not_raise(), id="ok_list_multiple"),
            pytest.param(
                -1,
                {},
                (),
                pytest.raises(AleBenchError, match=r"`seed` must be between 0 and 2\^64 \- 1\."),
                id="negative_seed",
            ),
            pytest.param(
                2**64,
                {},
                (),
                pytest.raises(AleBenchError, match=r"`seed` must be between 0 and 2\^64 \- 1\."),
                id="too_large_seed",
            ),
            pytest.param(42, {"N": 1}, ([42], {"N": 1}), does_not_raise(), id="ok_with_gen_kwargs"),
            pytest.param(
                42, {"N": 1, "M": 2}, ([42], {"N": 1, "M": 2}), does_not_raise(), id="ok_with_multiple_gen_kwargs"
            ),
            pytest.param(
                42,
                {"N": 1, "M": 2, "dir": "in2"},
                ([42], {"N": 1, "M": 2}),
                pytest.warns(UserWarning, match=r"`dir` is a reserved keyword and will be ignored\."),
                id="ok_with_multiple_gen_kwargs_with_dir",
            ),
        ],
    )
    def test_check_input_generation_arguments(
        self,
        dummy_session: Session,
        seed: int | None,
        gen_kwargs: dict[str, Any] | None,
        expected: tuple[list[int], dict[str, Any]],
        context: AbstractContextManager[None],
    ) -> None:
        with context:
            arguments = dummy_session._check_input_generation_arguments(seed=seed, gen_kwargs=gen_kwargs)
            assert arguments == expected

    @pytest.mark.parametrize(
        "input_str,output_str,expected,context",
        [
            pytest.param(
                "dummy input",
                "dummy output",
                (["dummy input"], ["dummy output"]),
                does_not_raise(),
                id="default_both_scalar",
            ),
            pytest.param(
                "dummy input",
                ["dummy output"],
                None,
                pytest.raises(
                    AleBenchError,
                    match=r"Both `input_str` and `output_str` must be either a string or a list of strings\.",
                ),
                id="default_input_scalar_output_list",
            ),
            pytest.param(
                ["dummy input"],
                "dummy output",
                None,
                pytest.raises(
                    AleBenchError,
                    match=r"Both `input_str` and `output_str` must be either a string or a list of strings\.",
                ),
                id="default_input_list_output_scalar",
            ),
            pytest.param(
                ["dummy input"],
                ["dummy output"],
                (["dummy input"], ["dummy output"]),
                does_not_raise(),
                id="default_both_list",
            ),
            pytest.param(
                ["dummy input 1", "dummy input 2", "dummy input 3"],
                ["dummy output 1", "dummy output 2", "dummy output 3"],
                (
                    ["dummy input 1", "dummy input 2", "dummy input 3"],
                    ["dummy output 1", "dummy output 2", "dummy output 3"],
                ),
                does_not_raise(),
                id="default_both_list_multiple",
            ),
            pytest.param(
                ["dummy input 1", "dummy input 2", "dummy input 3"],
                ["dummy output 1", "dummy output 2", "dummy output 3", " "],
                None,
                pytest.raises(
                    AleBenchError, match=r"The number of input strings and output strings must be the same\."
                ),
                id="default_both_list_different_length",
            ),
            pytest.param(
                "            ",
                "dummy output",
                None,
                pytest.raises(AleBenchError, match=r"The input string is empty\."),
                id="default_both_string_input_empty",
            ),
            pytest.param(
                "dummy input",
                "           ",
                None,
                pytest.raises(AleBenchError, match=r"The output string is empty\."),
                id="default_both_string_output_empty",
            ),
            pytest.param(
                ["dummy input 1", "               "],
                ["dummy output 1", "dummy output 2"],
                None,
                pytest.raises(AleBenchError, match=r"The input string is empty\."),
                id="default_list_string_input_empty",
            ),
            pytest.param(
                ["dummy input 1", "dummy input 2"],
                ["dummy output 1", "            "],
                None,
                pytest.raises(AleBenchError, match=r"The output string is empty\."),
                id="default_list_string_output_empty",
            ),
        ],
    )
    def test_check_local_visualization_arguments(
        self,
        dummy_session: Session,
        input_str: str | list[str],
        output_str: str | list[str],
        expected: tuple[list[str], list[str]] | None,
        context: AbstractContextManager[None],
    ) -> None:
        with context:
            arguments = dummy_session._check_local_visualization_arguments(input_str=input_str, output_str=output_str)
            assert arguments == expected

    @pytest.mark.parametrize(
        "input_str,code,code_language,judge_version,time_limit,memory_limit,expected,context",
        [
            pytest.param(
                "dummy input",
                "dummy code",
                CodeLanguage.RUST,
                JudgeVersion.V201907,
                5.0,
                1073741824,
                (["dummy input"], "dummy code", CodeLanguage.RUST, JudgeVersion.V201907, 5.0, 1073741824),
                does_not_raise(),
                id="default_case_scalar",
            ),
            pytest.param(
                ["dummy input"],
                "dummy code",
                CodeLanguage.RUST,
                JudgeVersion.V201907,
                5.0,
                1073741824,
                (["dummy input"], "dummy code", CodeLanguage.RUST, JudgeVersion.V201907, 5.0, 1073741824),
                does_not_raise(),
                id="default_case_list",
            ),
            pytest.param(
                ["dummy input 1", "dummy input 2", "dummy input 3"],
                "dummy code",
                CodeLanguage.RUST,
                JudgeVersion.V201907,
                5.0,
                1073741824,
                (
                    ["dummy input 1", "dummy input 2", "dummy input 3"],
                    "dummy code",
                    CodeLanguage.RUST,
                    JudgeVersion.V201907,
                    5.0,
                    1073741824,
                ),
                does_not_raise(),
                id="default_case_list_multiple",
            ),
            pytest.param(
                None,
                "dummy code",
                CodeLanguage.RUST,
                JudgeVersion.V201907,
                5.0,
                1073741824,
                ([""], "dummy code", CodeLanguage.RUST, JudgeVersion.V201907, 5.0, 1073741824),
                does_not_raise(),
                id="input_none",
            ),
            pytest.param(
                "",
                "dummy code",
                CodeLanguage.RUST,
                JudgeVersion.V201907,
                5.0,
                1073741824,
                (),
                pytest.raises(AleBenchError, match=r"The input string is empty\."),
                id="input_empty",
            ),
            pytest.param(
                "dummy input",
                None,
                CodeLanguage.RUST,
                JudgeVersion.V201907,
                5.0,
                1073741824,
                (),
                pytest.raises(AleBenchError, match=r"`code` must be specified\."),
                id="code_none",
            ),
            pytest.param(
                "dummy input",
                "",
                CodeLanguage.RUST,
                JudgeVersion.V201907,
                5.0,
                1073741824,
                (),
                pytest.raises(AleBenchError, match=r"The submission code is empty\."),
                id="code_empty",
            ),
            pytest.param(
                "dummy input",
                "a" * 524288,
                CodeLanguage.RUST,
                JudgeVersion.V201907,
                5.0,
                1073741824,
                (["dummy input"], "a" * 524288, CodeLanguage.RUST, JudgeVersion.V201907, 5.0, 1073741824),
                does_not_raise(),
                id="code_maximum_size",
            ),
            pytest.param(
                "dummy input",
                "a" * 524289,
                CodeLanguage.RUST,
                JudgeVersion.V201907,
                5.0,
                1073741824,
                (),
                pytest.raises(AleBenchError, match=r"The size of the submission code exceeds the limit \(512 KiB\)\."),
                id="code_too_large",
            ),
            pytest.param(
                "dummy input",
                "dummy code",
                None,
                JudgeVersion.V201907,
                5.0,
                1073741824,
                (),
                pytest.raises(AleBenchError, match=r"`code_language` must be specified\."),
                id="code_language_none",
            ),
            pytest.param(
                "dummy input",
                "dummy code",
                "rust",
                JudgeVersion.V201907,
                5.0,
                1073741824,
                (["dummy input"], "dummy code", CodeLanguage.RUST, JudgeVersion.V201907, 5.0, 1073741824),
                does_not_raise(),
                id="code_language_string_rust",
            ),
            pytest.param(
                "dummy input",
                "dummy code",
                "cpp14",
                JudgeVersion.V201907,
                5.0,
                1073741824,
                (),
                pytest.raises(AleBenchError, match=r"Invalid code language\. Available options: .+"),
                id="code_language_string_invalid",
            ),
            pytest.param(
                "dummy input",
                "dummy code",
                CodeLanguage.RUST,
                None,
                5.0,
                1073741824,
                (["dummy input"], "dummy code", CodeLanguage.RUST, JudgeVersion.V202301, 5.0, 1073741824),
                does_not_raise(),
                id="judge_version_none",
            ),
            pytest.param(
                "dummy input",
                "dummy code",
                CodeLanguage.RUST,
                "201907",
                5.0,
                1073741824,
                (["dummy input"], "dummy code", CodeLanguage.RUST, JudgeVersion.V201907, 5.0, 1073741824),
                does_not_raise(),
                id="judge_version_string",
            ),
            pytest.param(
                "dummy input",
                "dummy code",
                CodeLanguage.RUST,
                "201602",
                5.0,
                1073741824,
                (),
                pytest.raises(AleBenchError, match=r"Invalid judge version\. Available options: .+"),
                id="judge_version_string_invalid",
            ),
            pytest.param(
                "dummy input",
                "dummy code",
                "cpp23",
                "201907",
                5.0,
                1073741824,
                (),
                pytest.raises(AleBenchError, match=r"The judge version 201907 does not support C\+\+20 or C\+\+23\."),
                id="judge_version_invalid_pair",
            ),
            pytest.param(
                "dummy input",
                "dummy code",
                CodeLanguage.RUST,
                JudgeVersion.V201907,
                None,
                1073741824,
                (["dummy input"], "dummy code", CodeLanguage.RUST, JudgeVersion.V201907, 5.0, 1073741824),
                does_not_raise(),
                id="time_limit_none",
            ),
            pytest.param(
                "dummy input",
                "dummy code",
                CodeLanguage.RUST,
                JudgeVersion.V201907,
                0.0,
                1073741824,
                (),
                pytest.raises(AleBenchError, match=r"`time_limit` must be positive\."),
                id="time_limit_zero",
            ),
            pytest.param(
                "dummy input",
                "dummy code",
                CodeLanguage.RUST,
                JudgeVersion.V201907,
                -0.001,
                1073741824,
                (),
                pytest.raises(AleBenchError, match=r"`time_limit` must be positive\."),
                id="time_limit_negative",
            ),
            pytest.param(
                "dummy input",
                "dummy code",
                CodeLanguage.RUST,
                JudgeVersion.V201907,
                5.0,
                None,
                (["dummy input"], "dummy code", CodeLanguage.RUST, JudgeVersion.V201907, 5.0, 1073741824),
                does_not_raise(),
                id="memory_limit_none",
            ),
            pytest.param(
                "dummy input",
                "dummy code",
                CodeLanguage.RUST,
                JudgeVersion.V201907,
                5.0,
                "1073741824",
                (["dummy input"], "dummy code", CodeLanguage.RUST, JudgeVersion.V201907, 5.0, 1073741824),
                does_not_raise(),
                id="memory_limit_string",
            ),
            pytest.param(
                "dummy input",
                "dummy code",
                CodeLanguage.RUST,
                JudgeVersion.V201907,
                5.0,
                "1073741824b",
                (["dummy input"], "dummy code", CodeLanguage.RUST, JudgeVersion.V201907, 5.0, 1073741824),
                does_not_raise(),
                id="memory_limit_string_b",
            ),
            pytest.param(
                "dummy input",
                "dummy code",
                CodeLanguage.RUST,
                JudgeVersion.V201907,
                5.0,
                "1048576k",
                (["dummy input"], "dummy code", CodeLanguage.RUST, JudgeVersion.V201907, 5.0, 1073741824),
                does_not_raise(),
                id="memory_limit_string_k",
            ),
            pytest.param(
                "dummy input",
                "dummy code",
                CodeLanguage.RUST,
                JudgeVersion.V201907,
                5.0,
                "1024m",
                (["dummy input"], "dummy code", CodeLanguage.RUST, JudgeVersion.V201907, 5.0, 1073741824),
                does_not_raise(),
                id="memory_limit_string_m",
            ),
            pytest.param(
                "dummy input",
                "dummy code",
                CodeLanguage.RUST,
                JudgeVersion.V201907,
                5.0,
                "1g",
                (["dummy input"], "dummy code", CodeLanguage.RUST, JudgeVersion.V201907, 5.0, 1073741824),
                does_not_raise(),
                id="memory_limit_string_g",
            ),
            pytest.param(
                "dummy input",
                "dummy code",
                CodeLanguage.RUST,
                JudgeVersion.V201907,
                5.0,
                "1t",
                (),
                pytest.raises(
                    AleBenchError, match=r"Invalid `memory_limit` format\. Use 'b', 'k', 'm', or 'g' suffixes\."
                ),
                id="memory_limit_string_t",
            ),
            pytest.param(
                "dummy input",
                "dummy code",
                CodeLanguage.RUST,
                JudgeVersion.V201907,
                5.0,
                "1gb",
                (),
                pytest.raises(
                    AleBenchError, match=r"Invalid `memory_limit` format\. Use 'b', 'k', 'm', or 'g' suffixes\."
                ),
                id="memory_limit_string_invalid",
            ),
            pytest.param(
                "dummy input",
                "dummy code",
                CodeLanguage.RUST,
                JudgeVersion.V201907,
                5.0,
                4294967296,
                (["dummy input"], "dummy code", CodeLanguage.RUST, JudgeVersion.V201907, 5.0, 2147483648),
                does_not_raise(),
                id="memory_limit_too_large",
            ),
            pytest.param(
                "dummy input",
                "dummy code",
                CodeLanguage.RUST,
                JudgeVersion.V201907,
                5.0,
                "4096M",
                (["dummy input"], "dummy code", CodeLanguage.RUST, JudgeVersion.V201907, 5.0, 2147483648),
                does_not_raise(),
                id="memory_limit_too_large_string",
            ),
            pytest.param(
                "dummy input",
                "dummy code",
                CodeLanguage.RUST,
                JudgeVersion.V201907,
                5.0,
                6291455,
                (),
                pytest.raises(AleBenchError, match=r"`memory_limit` must be greater than or equal to 6MB\."),
                id="memory_limit_too_small",
            ),
            pytest.param(
                "dummy input",
                "dummy code",
                CodeLanguage.RUST,
                JudgeVersion.V201907,
                5.0,
                "6291455B",
                (),
                pytest.raises(AleBenchError, match=r"`memory_limit` must be greater than or equal to 6MB\."),
                id="memory_limit_too_small_string",
            ),
        ],
    )
    def test_check_run_cases_arguments(
        self,
        dummy_session: Session,
        input_str: str | None,
        code: str | None,
        code_language: CodeLanguage | str | None,
        judge_version: JudgeVersion | str | None,
        time_limit: float | None,
        memory_limit: int | str | None,
        expected: tuple[list[str], str, CodeLanguage, JudgeVersion, float, int],
        context: AbstractContextManager[None],
    ) -> None:
        with context:
            arguments = dummy_session._check_run_cases_arguments(
                input_str=input_str,
                code=code,
                code_language=code_language,
                judge_version=judge_version,
                time_limit=time_limit,
                memory_limit=memory_limit,
            )
            assert arguments == expected
