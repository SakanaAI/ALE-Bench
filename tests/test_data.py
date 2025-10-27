from __future__ import annotations

import datetime as dt
from contextlib import AbstractContextManager, nullcontext as does_not_raise

import pytest

from ale_bench.data import (
    ProblemMetaData,
    ProblemType,
    RankPerformanceMap,
    RankingCalculator,
    RatingCalculator,
    RelativeResults,
    RelativeScoreType,
    ScoreType,
    Standings,
)
from ale_bench.result import CaseResult, JudgeResult, ResourceUsage, Result


class TestRankPerformanceMap:
    @pytest.mark.parametrize(
        "raw_data,context,data",
        [
            pytest.param(
                [], pytest.raises(ValueError, match=r"The raw data must contain at least 2 entries\."), {}, id="empty"
            ),
            pytest.param(
                [(1, 3200)],
                pytest.raises(ValueError, match=r"The raw data must contain at least 2 entries\."),
                {1.0: 3200},
                id="1row",
            ),
            pytest.param(
                [(1, 3200), (2, 200)],
                does_not_raise(),
                {1.0: 3200, 2.0: 200},
                id="2rows",
            ),
            pytest.param(
                [(1, 3200), (2, 3199), (3, 200)],
                does_not_raise(),
                {1.0: 3200, 2.0: 3199, 3.0: 200},
                id="3rows",
            ),
            pytest.param(
                [(2, 3200), (1, 3199), (3, 200)],
                pytest.raises(ValueError, match=r"The rank must be sorted in ascending order\."),
                {},
                id="3rows_rank_not_sorted",
            ),
            pytest.param(
                [(1, 3199), (2, 3200), (3, 200)],
                pytest.raises(ValueError, match=r"The performance must be sorted in descending order\."),
                {},
                id="3rows_performance_not_sorted",
            ),
            pytest.param(
                [(1, 3200), (2, 2800), (3, 2400), (4, 200)],
                does_not_raise(),
                {1.0: 3200, 2.0: 2800, 3.0: 2400, 4.0: 200},
                id="4rows",
            ),
            pytest.param(
                [(1, 3200), (2, 2800), (3, 2000), (5, 200)],
                does_not_raise(),
                {1.0: 3200, 2.0: 2800, 3.5: 2000, 5.0: 200},
                id="4rows_with_tie",
            ),
            pytest.param(
                [(1, 3200), (2, 2800), (4, 2000), (8, 200)],
                does_not_raise(),
                {1.0: 3200, 2.5: 2800, 5.5: 2000, 8.0: 200},
                id="4rows_with_ties",
            ),
            pytest.param(
                [(idx, 3200 - 32 * idx) for idx in list(range(1, 101))],
                does_not_raise(),
                {float(idx): 3200 - 32 * idx for idx in list(range(1, 101))},
                id="100rows",
            ),
            pytest.param(
                [(idx, 3200 - 32 * idx) for idx in list(range(1, 88))]
                + [(89, 384), (88, 352)]
                + [(idx, 3200 - 32 * idx) for idx in list(range(90, 101))],
                pytest.raises(ValueError, match=r"The rank must be sorted in ascending order\."),
                {},
                id="100rows_rank_not_sorted",
            ),
            pytest.param(
                [(idx, 3200 - 32 * idx) for idx in list(range(1, 88))]
                + [(88, 352), (89, 384)]
                + [(idx, 3200 - 32 * idx) for idx in list(range(90, 101))],
                pytest.raises(ValueError, match=r"The performance must be sorted in descending order\."),
                {},
                id="100rows_performance_not_sorted",
            ),
        ],
    )
    def test_init(
        self,
        raw_data: list[tuple[int, int]],
        context: AbstractContextManager[None],
        data: dict[float, int],
    ) -> None:
        with context:
            rank_performance_map = RankPerformanceMap(raw_data=raw_data)
            assert rank_performance_map.raw_data == raw_data
            assert rank_performance_map.data == data

    @pytest.mark.parametrize(
        "raw_data,rank,context,expected",
        [
            pytest.param([(1, 3200), (2, 200)], 1, does_not_raise(), 3200, id="2rows_1st"),
            pytest.param([(1, 3200), (2, 200)], 1.5, does_not_raise(), 1700, id="2rows_1.5th"),
            pytest.param([(1, 3200), (2, 200)], 2, does_not_raise(), 200, id="2rows_2nd"),
            pytest.param(
                [(1, 3200), (2, 200)],
                2.01,
                pytest.raises(
                    RuntimeError, match=r"Something went wrong: `win` should be less than `len\(sorted_keys\)`\."
                ),
                0,
                id="2rows_not_within_2nd",
            ),
            pytest.param([(1, 3200), (2, 2800), (3, 200)], 1.0, does_not_raise(), 3200, id="3rows_1st"),
            pytest.param([(1, 3200), (2, 2800), (3, 200)], 1.5, does_not_raise(), 3000, id="3rows_1.5th"),
            pytest.param([(1, 3200), (2, 2800), (3, 200)], 2.0, does_not_raise(), 2800, id="3rows_2nd"),
            pytest.param([(1, 3200), (2, 2800), (3, 200)], 2.5, does_not_raise(), 1500, id="3rows_2.5th"),
            pytest.param([(1, 3200), (2, 2800), (3, 200)], 3.0, does_not_raise(), 200, id="3rows_3rd"),
            pytest.param(
                [(1, 3200), (2, 2800), (3, 200)],
                3.14,
                pytest.raises(
                    RuntimeError, match=r"Something went wrong: `win` should be less than `len\(sorted_keys\)`\."
                ),
                0,
                id="3rows_not_within_3rd",
            ),
            pytest.param([(1, 3200), (99, 2800), (100, 200)], 1, does_not_raise(), 3592, id="3rows_n100_1st"),
            pytest.param([(1, 3200), (99, 2800), (100, 200)], 49.5, does_not_raise(), 3200, id="3rows_n100_49.5th"),
            pytest.param([(1, 3200), (99, 2800), (100, 200)], 99, does_not_raise(), 2800, id="3rows_n100_99th"),
            pytest.param([(1, 3200), (99, 2800), (100, 200)], 99.5, does_not_raise(), 1500, id="3rows_n100_99.5th"),
            pytest.param([(1, 3200), (99, 2800), (100, 200)], 100, does_not_raise(), 200, id="3rows_n100_100th"),
            pytest.param(
                [(1, 3200), (99, 2800), (100, 200)],
                101,
                pytest.raises(
                    RuntimeError, match=r"Something went wrong: `win` should be less than `len\(sorted_keys\)`\."
                ),
                0,
                id="3rows_n100_not_within_100th",
            ),
            pytest.param([(1, 3000), (3, 2400), (4, 200)], 1.0, does_not_raise(), 3200, id="3rows_tied1st_1st"),
            pytest.param([(1, 3000), (3, 2400), (4, 200)], 1.5, does_not_raise(), 3000, id="3rows_tied1st_1.5th"),
            pytest.param([(1, 3000), (3, 2400), (4, 200)], 3.0, does_not_raise(), 2400, id="3rows_tied1st_3rd"),
            pytest.param([(1, 3000), (3, 2400), (4, 200)], 3.5, does_not_raise(), 1300, id="3rows_tied1st_3.5th"),
            pytest.param([(1, 3000), (3, 2400), (4, 200)], 4.0, does_not_raise(), 200, id="3rows_tied1st_4th"),
            pytest.param([(1, 3200), (2, 2800), (3, 2000), (4, 200)], 1.0, does_not_raise(), 3200, id="4rows_1st"),
            pytest.param([(1, 3200), (2, 2800), (3, 2000), (4, 200)], 1.5, does_not_raise(), 3000, id="4rows_1s.5th"),
            pytest.param([(1, 3200), (2, 2800), (3, 2000), (4, 200)], 2.0, does_not_raise(), 2800, id="4rows_2nd"),
            pytest.param([(1, 3200), (2, 2800), (3, 2000), (4, 200)], 2.5, does_not_raise(), 2400, id="4rows_2.5th"),
            pytest.param([(1, 3200), (2, 2800), (3, 2000), (4, 200)], 3.0, does_not_raise(), 2000, id="4rows_3rd"),
            pytest.param([(1, 3200), (2, 2800), (3, 2000), (4, 200)], 3.5, does_not_raise(), 1100, id="4rows_3.5th"),
            pytest.param([(1, 3200), (2, 2800), (3, 2000), (4, 200)], 4.0, does_not_raise(), 200, id="4rows_4th"),
            pytest.param(
                [(1, 3200), (2, 2800), (4, 2400), (8, 2000), (16, 200)],
                1.0,
                does_not_raise(),
                3200,
                id="5rows_n16_1st",
            ),
            pytest.param(
                [(1, 3200), (2, 2800), (4, 2400), (8, 2000), (16, 200)],
                1.5,
                does_not_raise(),
                3067,
                id="5rows_n16_1.5th",
            ),
            pytest.param(
                [(1, 3200), (2, 2800), (4, 2400), (8, 2000), (16, 200)],
                2.0,
                does_not_raise(),
                2933,
                id="5rows_n16_2nd",
            ),
            pytest.param(
                [(1, 3200), (2, 2800), (4, 2400), (8, 2000), (16, 200)],
                2.5,
                does_not_raise(),
                2800,
                id="5rows_n16_2.5th",
            ),
            pytest.param(
                [(1, 3200), (2, 2800), (4, 2400), (8, 2000), (16, 200)],
                4.0,
                does_not_raise(),
                2600,
                id="5rows_n16_4th",
            ),
            pytest.param(
                [(1, 3200), (2, 2800), (4, 2400), (8, 2000), (16, 200)],
                6.0,
                does_not_raise(),
                2367,
                id="5rows_n16_6th",
            ),
            pytest.param(
                [(1, 3200), (2, 2800), (4, 2400), (8, 2000), (16, 200)],
                8.0,
                does_not_raise(),
                2233,
                id="5rows_n16_8th",
            ),
            pytest.param(
                [(1, 3200), (2, 2800), (4, 2400), (8, 2000), (16, 200)],
                12.0,
                does_not_raise(),
                1800,
                id="5rows_n16_12nd",
            ),
            pytest.param(
                [(1, 3200), (2, 2800), (4, 2400), (8, 2000), (16, 200)],
                16.0,
                does_not_raise(),
                200,
                id="5rows_n16_16th",
            ),
            pytest.param(
                [(idx, 4000 - 40 * idx) for idx in list(range(1, 101))],
                1.0,
                does_not_raise(),
                3960,
                id="100rows_1st",
            ),
            pytest.param(
                [(idx, 4000 - 40 * idx) for idx in list(range(1, 101))],
                1.5,
                does_not_raise(),
                3940,
                id="100rows_1.5th",
            ),
            pytest.param(
                [(idx, 4000 - 40 * idx) for idx in list(range(1, 101))],
                59.0,
                does_not_raise(),
                1640,
                id="100rows_59th",
            ),
        ],
    )
    def test_get_performance(
        self, raw_data: list[tuple[int, int]], rank: int | float, context: AbstractContextManager[None], expected: int
    ) -> None:
        rank_performance_map = RankPerformanceMap(raw_data=raw_data)
        with context:
            assert rank_performance_map.get_performance(rank) == expected


class TestRelativeResults:
    @pytest.mark.parametrize(
        "absolute_scores,relative_score_type,relative_max_score,context,expected_absolute_scores",
        [
            pytest.param(
                [],
                RelativeScoreType.MAX,
                1000000,
                pytest.raises(ValueError, match=r"The relative results absolute_scores cannot be empty\."),
                [],
                id="no_case",
            ),
            pytest.param(
                [[]],
                RelativeScoreType.MAX,
                1000000,
                pytest.raises(ValueError, match=r"The number of participants must be greater than 0\."),
                [],
                id="no_participants",
            ),
            pytest.param(
                [[100], [100], [100, 200]],
                RelativeScoreType.MAX,
                1000000,
                pytest.raises(ValueError, match=r"The number of participants must be the same for all cases\."),
                [],
                id="different_num_participants",
            ),
            pytest.param(
                [[100, 200, -1, 300, -1], [200, 400, -1, 100, 100]],
                RelativeScoreType.MAX,
                1000000,
                does_not_raise(),
                [[100, 200, -1, 300, -1], [200, 400, -1, 100, 100]],
                id="max",
            ),
            pytest.param(
                [[100, 200, -1, 300, -1], [200, 400, -1, 100, 500]],
                RelativeScoreType.MIN,
                1000000,
                does_not_raise(),
                [[100, 200, -1, 300, -1], [200, 400, -1, 100, 500]],
                id="min",
            ),
            pytest.param(
                [[100, 200, -1, 300, -1], [200, 400, -1, 100, 100]],
                RelativeScoreType.RANK_MAX,
                1000000,
                does_not_raise(),
                [[100, 200, -1, 300, -1], [200, 400, -1, 100, 100]],
                id="rank_max",
            ),
            pytest.param(
                [[100, 200, -1, 300, -1], [200, 400, -1, 100, 500]],
                RelativeScoreType.RANK_MIN,
                1000000,
                does_not_raise(),
                [[100, 200, -1, 300, -1], [200, 400, -1, 100, 500]],
                id="min",
            ),
        ],
    )
    def test_init(
        self,
        absolute_scores: list[list[int]],
        relative_score_type: RelativeScoreType,
        relative_max_score: int,
        context: AbstractContextManager[None],
        expected_absolute_scores: list[list[int]],
    ) -> None:
        with context:
            relative_results = RelativeResults(
                absolute_scores=absolute_scores,
                relative_score_type=relative_score_type,
                relative_max_score=relative_max_score,
            )
            assert relative_results.absolute_scores == expected_absolute_scores

    @pytest.mark.parametrize(
        "new_scores,relative_score_type,context,expected",
        [
            pytest.param(
                [500],
                RelativeScoreType.MAX,
                pytest.raises(
                    ValueError, match=r"The number of new scores \(1\) must be the same as the number of cases \(2\)\."
                ),
                (0, []),
                id="new_scores_shorter",
            ),
            pytest.param(
                [500, 500, 500],
                RelativeScoreType.MAX,
                pytest.raises(
                    ValueError, match=r"The number of new scores \(3\) must be the same as the number of cases \(2\)\."
                ),
                (0, []),
                id="new_scores_longer",
            ),
            pytest.param(
                [400, 300],
                RelativeScoreType.MAX,
                does_not_raise(),
                (
                    1750,
                    [1000, 750],
                    sorted([250 + 500, 500 + 1000, 0 + 0, 750 + 250, 0 + 250, 1000 + 750], reverse=True),
                ),
                id="new_scores_max",
            ),
            pytest.param(
                [500, 500],
                RelativeScoreType.MAX,
                does_not_raise(),
                (
                    2000,
                    [1000, 1000],
                    sorted([200 + 400, 400 + 800, 0 + 0, 600 + 200, 0 + 200, 1000 + 1000], reverse=True),
                ),
                id="new_scores_max_top",
            ),
            pytest.param(
                [400, 50],
                RelativeScoreType.MIN,
                does_not_raise(),
                (
                    1250,
                    [250, 1000],
                    sorted([1000 + 250, 500 + 125, 0 + 0, 333 + 500, 0 + 500, 250 + 1000], reverse=True),
                ),
                id="new_scores_min",
            ),
            pytest.param(
                [100, 100],
                RelativeScoreType.MIN,
                does_not_raise(),
                (
                    2000,
                    [1000, 1000],
                    sorted([1000 + 500, 500 + 250, 0 + 0, 333 + 1000, 0 + 1000, 1000 + 1000], reverse=True),
                ),
                id="new_scores_min_top",
            ),
            pytest.param(
                [400, 300],
                RelativeScoreType.RANK_MAX,
                does_not_raise(),
                (
                    1833,
                    [1000, 833],
                    sorted([500 + 667, 667 + 1000, 0 + 0, 833 + 417, 0 + 417, 1000 + 833], reverse=True),
                ),
                id="new_scores_rank_max",
            ),
            pytest.param(
                [500, 500],
                RelativeScoreType.RANK_MAX,
                does_not_raise(),
                (
                    2000,
                    [1000, 1000],
                    sorted([500 + 667, 667 + 833, 0 + 0, 833 + 417, 0 + 417, 1000 + 1000], reverse=True),
                ),
                id="new_scores_rank_max_top",
            ),
            pytest.param(
                [400, 50],
                RelativeScoreType.RANK_MIN,
                does_not_raise(),
                (
                    1500,
                    [500, 1000],
                    sorted([1000 + 500, 833 + 333, 0 + 0, 667 + 750, 0 + 750, 500 + 1000], reverse=True),
                ),
                id="new_scores_min",
            ),
            pytest.param(
                [100, 100],
                RelativeScoreType.RANK_MIN,
                does_not_raise(),
                (
                    1750,
                    [917, 833],
                    sorted([917 + 500, 667 + 333, 0 + 0, 500 + 833, 0 + 833, 917 + 833], reverse=True),
                ),
                id="new_scores_rank_min_top",
            ),
        ],
    )
    def test_calculate_relative_score(
        self,
        new_scores: list[int],
        relative_score_type: RelativeScoreType,
        context: AbstractContextManager[None],
        expected: tuple[int, list[int], list[int]],
    ) -> None:
        relative_results = RelativeResults(
            absolute_scores=[[100, 200, -1, 300, -1], [200, 400, -1, 100, 100]],
            relative_score_type=relative_score_type,
            relative_max_score=1000,
        )
        with context:
            assert relative_results.recalculate_relative_score(new_scores) == expected


class TestStandings:
    @pytest.mark.parametrize(
        "standings_scores,context,score_rank_list",
        [
            pytest.param(
                [], pytest.raises(ValueError, match=r"The standings scores cannot be empty\."), [], id="empty"
            ),
            pytest.param(
                [(1, 100)],
                pytest.raises(ValueError, match=r"The last entry must be an entry with score 0\."),
                [],
                id="1row_no_score0",
            ),
            pytest.param(
                [(1, 100), (2, 0)],
                does_not_raise(),
                [(100, 1, 1), (0, 2, 2)],
                id="2rows",
            ),
            pytest.param(
                [(1, 100), (2, 99)],
                pytest.raises(ValueError, match=r"The last entry must be an entry with score 0\."),
                [],
                id="2rows_no_score0",
            ),
            pytest.param(
                [(1, 100), (2, 99), (3, 0)],
                does_not_raise(),
                [(100, 1, 1), (99, 2, 2), (0, 3, 3)],
                id="3rows",
            ),
            pytest.param(
                [(2, 100), (1, 99), (3, 0)],
                pytest.raises(ValueError, match=r"The rank must be sorted in ascending order\."),
                [],
                id="3rows_rank_not_sorted",
            ),
            pytest.param(
                [(1, 99), (2, 100), (3, 0)],
                pytest.raises(ValueError, match=r"The score must be sorted in descending order\."),
                [],
                id="3rows_score_not_sorted",
            ),
            pytest.param(
                [(1, 100), (2, 0), (3, 0)],
                pytest.raises(ValueError, match=r"The score must be greater than 0 except for the last entry\."),
                [],
                id="3rows_not_last_entry_with_score0",
            ),
            pytest.param(
                [
                    (
                        1,
                        100,
                    ),
                    (2, -1),
                    (3, -2),
                ],
                pytest.raises(ValueError, match=r"The score must be greater than 0 except for the last entry\."),
                [],
                id="3rows_not_last_entry_with_negative_score",
            ),
            pytest.param(
                [(1, 100), (2, 99), (3, -1)],
                pytest.raises(ValueError, match=r"The last entry must be an entry with score 0\."),
                [],
                id="3rows_last_entry_with_negative_score",
            ),
            pytest.param(
                [(1, 100), (2, 99), (3, 97), (4, 0)],
                does_not_raise(),
                [(100, 1, 1), (99, 2, 2), (97, 3, 3), (0, 4, 4)],
                id="4rows",
            ),
            pytest.param(
                [(1, 100), (2, 99), (3, 97), (5, 0)],
                does_not_raise(),
                [(100, 1, 1), (99, 2, 2), (97, 3, 4), (0, 5, 5)],
                id="4rows_with_tie",
            ),
            pytest.param(
                [(1, 100), (2, 98), (4, 96), (8, 0)],
                does_not_raise(),
                [(100, 1, 1), (98, 2, 3), (96, 4, 7), (0, 8, 8)],
                id="4rows_with_ties",
            ),
            pytest.param(
                [(idx, 100 - idx) for idx in list(range(1, 101))],
                does_not_raise(),
                [(100 - idx, idx, idx) for idx in list(range(1, 101))],
                id="100rows",
            ),
            pytest.param(
                [(idx, 100 - idx) for idx in list(range(1, 88))]
                + [(89, 12), (88, 11)]
                + [(idx, 100 - idx) for idx in list(range(90, 101))],
                pytest.raises(ValueError, match=r"The rank must be sorted in ascending order\."),
                [],
                id="100rows_rank_not_sorted",
            ),
            pytest.param(
                [(idx, 100 - idx) for idx in list(range(1, 88))]
                + [(88, 12), (89, 13)]
                + [(idx, 100 - idx) for idx in list(range(90, 101))],
                pytest.raises(ValueError, match=r"The score must be sorted in descending order\."),
                [],
                id="100rows_score_not_sorted",
            ),
            pytest.param(
                [(idx, 100 - idx) for idx in list(range(1, 102))],
                pytest.raises(ValueError, match=r"The score must be greater than 0 except for the last entry\."),
                [],
                id="101rows_not_last_entry_with_score0",
            ),
        ],
    )
    def test_init(
        self,
        standings_scores: list[tuple[int, int]],
        context: AbstractContextManager[None],
        score_rank_list: list[tuple[int, int, int]],
    ) -> None:
        with context:
            standings = Standings(standings_scores=standings_scores)
            assert standings.standings_scores == standings_scores
            assert standings.score_rank_list == score_rank_list

    @pytest.mark.parametrize(
        "standings_scores,result,expected",
        [
            pytest.param(
                [(1, 0)],
                Result(
                    allow_score_non_ac=True,
                    resource_usage=ResourceUsage(),
                    case_results=[
                        CaseResult(
                            judge_result=JudgeResult.ACCEPTED,
                            message="",
                            absolute_score=1,
                            execution_time=0.0,
                            memory_usage=0,
                        ),
                    ],
                ),
                (1, 1.0, [1]),
                id="1row_1st",
            ),
            pytest.param(
                [(1, 0)],
                Result(
                    allow_score_non_ac=True,
                    resource_usage=ResourceUsage(),
                    case_results=[
                        CaseResult(
                            judge_result=JudgeResult.ACCEPTED,
                            message="",
                            absolute_score=0,
                            execution_time=0.0,
                            memory_usage=0,
                        ),
                    ],
                ),
                (1, 1.0, [0]),
                id="1row_1st_tie",
            ),
            pytest.param(
                [(1, 100), (2, 0)],
                Result(
                    allow_score_non_ac=True,
                    resource_usage=ResourceUsage(),
                    case_results=[
                        CaseResult(
                            judge_result=JudgeResult.ACCEPTED,
                            message="",
                            absolute_score=101,
                            execution_time=0.0,
                            memory_usage=0,
                        ),
                    ],
                ),
                (1, 1.0, [101]),
                id="2rows_1st",
            ),
            pytest.param(
                [(1, 100), (2, 0)],
                Result(
                    allow_score_non_ac=True,
                    resource_usage=ResourceUsage(),
                    case_results=[
                        CaseResult(
                            judge_result=JudgeResult.ACCEPTED,
                            message="",
                            absolute_score=100,
                            execution_time=0.0,
                            memory_usage=0,
                        ),
                    ],
                ),
                (1, 1.0, [100]),
                id="2rows_1st_tie",
            ),
            pytest.param(
                [(1, 100), (2, 0)],
                Result(
                    allow_score_non_ac=True,
                    resource_usage=ResourceUsage(),
                    case_results=[
                        CaseResult(
                            judge_result=JudgeResult.ACCEPTED,
                            message="",
                            absolute_score=99,
                            execution_time=0.0,
                            memory_usage=0,
                        ),
                    ],
                ),
                (2, 2.0, [99]),
                id="2rows_2nd",
            ),
            pytest.param(
                [(1, 100), (2, 0)],
                Result(
                    allow_score_non_ac=True,
                    resource_usage=ResourceUsage(),
                    case_results=[
                        CaseResult(
                            judge_result=JudgeResult.ACCEPTED,
                            message="",
                            absolute_score=0,
                            execution_time=0.0,
                            memory_usage=0,
                        ),
                    ],
                ),
                (2, 2.0, [0]),
                id="2rows_2nd_tie",
            ),
            pytest.param(
                [(1, 100), (2, 99), (3, 0)],
                Result(
                    allow_score_non_ac=True,
                    resource_usage=ResourceUsage(),
                    case_results=[
                        CaseResult(
                            judge_result=JudgeResult.ACCEPTED,
                            message="",
                            absolute_score=101,
                            execution_time=0.0,
                            memory_usage=0,
                        ),
                    ],
                ),
                (1, 1.0, [101]),
                id="3rows_1st",
            ),
            pytest.param(
                [(1, 100), (2, 99), (3, 0)],
                Result(
                    allow_score_non_ac=True,
                    resource_usage=ResourceUsage(),
                    case_results=[
                        CaseResult(
                            judge_result=JudgeResult.ACCEPTED,
                            message="",
                            absolute_score=100,
                            execution_time=0.0,
                            memory_usage=0,
                        ),
                    ],
                ),
                (1, 1.0, [100]),
                id="3rows_1st_tie",
            ),
            pytest.param(
                [(1, 100), (2, 99), (3, 0)],
                Result(
                    allow_score_non_ac=True,
                    resource_usage=ResourceUsage(),
                    case_results=[
                        CaseResult(
                            judge_result=JudgeResult.ACCEPTED,
                            message="",
                            absolute_score=99,
                            execution_time=0.0,
                            memory_usage=0,
                        ),
                    ],
                ),
                (2, 2.0, [99]),
                id="3rows_2nd_tie",
            ),
            pytest.param(
                [(1, 100), (2, 99), (3, 0)],
                Result(
                    allow_score_non_ac=True,
                    resource_usage=ResourceUsage(),
                    case_results=[
                        CaseResult(
                            judge_result=JudgeResult.ACCEPTED,
                            message="",
                            absolute_score=98,
                            execution_time=0.0,
                            memory_usage=0,
                        ),
                    ],
                ),
                (3, 3.0, [98]),
                id="3rows_3rd",
            ),
            pytest.param(
                [(1, 100), (2, 99), (3, 0)],
                Result(
                    allow_score_non_ac=True,
                    resource_usage=ResourceUsage(),
                    case_results=[
                        CaseResult(
                            judge_result=JudgeResult.ACCEPTED,
                            message="",
                            absolute_score=0,
                            execution_time=0.0,
                            memory_usage=0,
                        ),
                    ],
                ),
                (3, 3.0, [0]),
                id="3rows_3rd_tie",
            ),
            pytest.param(
                [(1, 100), (99, 99), (100, 0)],
                Result(
                    allow_score_non_ac=True,
                    resource_usage=ResourceUsage(),
                    case_results=[
                        CaseResult(
                            judge_result=JudgeResult.ACCEPTED,
                            message="",
                            absolute_score=101,
                            execution_time=0.0,
                            memory_usage=0,
                        ),
                    ],
                ),
                (1, 1.0, [101]),
                id="3rows_n99_1st",
            ),
            pytest.param(
                [(1, 100), (99, 99), (100, 0)],
                Result(
                    allow_score_non_ac=True,
                    resource_usage=ResourceUsage(),
                    case_results=[
                        CaseResult(
                            judge_result=JudgeResult.ACCEPTED,
                            message="",
                            absolute_score=100,
                            execution_time=0.0,
                            memory_usage=0,
                        ),
                    ],
                ),
                (1, 49.5, [100]),
                id="3rows_n99_1st_tie",
            ),
            pytest.param(
                [(1, 100), (99, 99), (100, 0)],
                Result(
                    allow_score_non_ac=True,
                    resource_usage=ResourceUsage(),
                    case_results=[
                        CaseResult(
                            judge_result=JudgeResult.ACCEPTED,
                            message="",
                            absolute_score=99,
                            execution_time=0.0,
                            memory_usage=0,
                        ),
                    ],
                ),
                (99, 99.0, [99]),
                id="3rows_n99_99th_tie",
            ),
            pytest.param(
                [(1, 100), (99, 99), (100, 0)],
                Result(
                    allow_score_non_ac=True,
                    resource_usage=ResourceUsage(),
                    case_results=[
                        CaseResult(
                            judge_result=JudgeResult.ACCEPTED,
                            message="",
                            absolute_score=98,
                            execution_time=0.0,
                            memory_usage=0,
                        ),
                    ],
                ),
                (100, 100.0, [98]),
                id="3rows_n99_10th",
            ),
            pytest.param(
                [(1, 100), (99, 99), (100, 0)],
                Result(
                    allow_score_non_ac=True,
                    resource_usage=ResourceUsage(),
                    case_results=[
                        CaseResult(
                            judge_result=JudgeResult.ACCEPTED,
                            message="",
                            absolute_score=0,
                            execution_time=0.0,
                            memory_usage=0,
                        ),
                    ],
                ),
                (100, 100.0, [0]),
                id="3rows_n99_100th_tie",
            ),
            pytest.param(
                [(1, 100), (2, 99), (3, 97), (4, 0)],
                Result(
                    allow_score_non_ac=True,
                    resource_usage=ResourceUsage(),
                    case_results=[
                        CaseResult(
                            judge_result=JudgeResult.ACCEPTED,
                            message="",
                            absolute_score=61,
                            execution_time=0.0,
                            memory_usage=0,
                        ),
                        CaseResult(
                            judge_result=JudgeResult.ACCEPTED,
                            message="",
                            absolute_score=40,
                            execution_time=0.0,
                            memory_usage=0,
                        ),
                    ],
                ),
                (1, 1.0, [61, 40]),
                id="4rows_1st",
            ),
            pytest.param(
                [(1, 100), (2, 99), (3, 97), (4, 0)],
                Result(
                    allow_score_non_ac=True,
                    resource_usage=ResourceUsage(),
                    case_results=[
                        CaseResult(
                            judge_result=JudgeResult.ACCEPTED,
                            message="",
                            absolute_score=61,
                            execution_time=0.0,
                            memory_usage=0,
                        ),
                        CaseResult(
                            judge_result=JudgeResult.ACCEPTED,
                            message="",
                            absolute_score=39,
                            execution_time=0.0,
                            memory_usage=0,
                        ),
                    ],
                ),
                (1, 1.0, [61, 39]),
                id="4rows_1st_tie",
            ),
            pytest.param(
                [(1, 100), (2, 99), (3, 97), (4, 0)],
                Result(
                    allow_score_non_ac=True,
                    resource_usage=ResourceUsage(),
                    case_results=[
                        CaseResult(
                            judge_result=JudgeResult.ACCEPTED,
                            message="",
                            absolute_score=60,
                            execution_time=0.0,
                            memory_usage=0,
                        ),
                        CaseResult(
                            judge_result=JudgeResult.ACCEPTED,
                            message="",
                            absolute_score=39,
                            execution_time=0.0,
                            memory_usage=0,
                        ),
                    ],
                ),
                (2, 2.0, [60, 39]),
                id="4rows_2nd_tie",
            ),
            pytest.param(
                [(1, 100), (2, 99), (3, 97), (4, 0)],
                Result(
                    allow_score_non_ac=True,
                    resource_usage=ResourceUsage(),
                    case_results=[
                        CaseResult(
                            judge_result=JudgeResult.ACCEPTED,
                            message="",
                            absolute_score=60,
                            execution_time=0.0,
                            memory_usage=0,
                        ),
                        CaseResult(
                            judge_result=JudgeResult.ACCEPTED,
                            message="",
                            absolute_score=38,
                            execution_time=0.0,
                            memory_usage=0,
                        ),
                    ],
                ),
                (3, 3.0, [60, 38]),
                id="4rows_3rd",
            ),
            pytest.param(
                [(1, 100), (2, 99), (3, 97), (4, 0)],
                Result(
                    allow_score_non_ac=True,
                    resource_usage=ResourceUsage(),
                    case_results=[
                        CaseResult(
                            judge_result=JudgeResult.ACCEPTED,
                            message="",
                            absolute_score=59,
                            execution_time=0.0,
                            memory_usage=0,
                        ),
                        CaseResult(
                            judge_result=JudgeResult.ACCEPTED,
                            message="",
                            absolute_score=38,
                            execution_time=0.0,
                            memory_usage=0,
                        ),
                    ],
                ),
                (3, 3.0, [59, 38]),
                id="4rows_3rd_tie",
            ),
            pytest.param(
                [(1, 100), (2, 99), (3, 97), (4, 0)],
                Result(
                    allow_score_non_ac=True,
                    resource_usage=ResourceUsage(),
                    case_results=[
                        CaseResult(
                            judge_result=JudgeResult.ACCEPTED,
                            message="",
                            absolute_score=59,
                            execution_time=0.0,
                            memory_usage=0,
                        ),
                        CaseResult(
                            judge_result=JudgeResult.ACCEPTED,
                            message="",
                            absolute_score=37,
                            execution_time=0.0,
                            memory_usage=0,
                        ),
                    ],
                ),
                (4, 4.0, [59, 37]),
                id="4rows_4th",
            ),
            pytest.param(
                [(1, 100), (2, 99), (3, 97), (4, 0)],
                Result(
                    allow_score_non_ac=True,
                    resource_usage=ResourceUsage(),
                    case_results=[
                        CaseResult(
                            judge_result=JudgeResult.ACCEPTED,
                            message="",
                            absolute_score=0,
                            execution_time=0.0,
                            memory_usage=0,
                        ),
                        CaseResult(
                            judge_result=JudgeResult.WRONG_ANSWER,
                            message="",
                            absolute_score=0,
                            execution_time=0.0,
                            memory_usage=0,
                        ),
                    ],
                ),
                (4, 4.0, [0, 0]),
                id="4rows_4th_tie",
            ),
            pytest.param(
                [(1, 100), (2, 98), (4, 96), (8, 94), (16, 0)],
                Result(
                    allow_score_non_ac=True,
                    resource_usage=ResourceUsage(),
                    case_results=[
                        CaseResult(
                            judge_result=JudgeResult.ACCEPTED,
                            message="",
                            absolute_score=101,
                            execution_time=0.0,
                            memory_usage=0,
                        ),
                    ],
                ),
                (1, 1.0, [101]),
                id="5rows_n16_1st",
            ),
            pytest.param(
                [(1, 100), (2, 98), (4, 96), (8, 94), (16, 0)],
                Result(
                    allow_score_non_ac=True,
                    resource_usage=ResourceUsage(),
                    case_results=[
                        CaseResult(
                            judge_result=JudgeResult.ACCEPTED,
                            message="",
                            absolute_score=100,
                            execution_time=0.0,
                            memory_usage=0,
                        ),
                    ],
                ),
                (1, 1.0, [100]),
                id="5rows_n16_1st_tie",
            ),
            pytest.param(
                [(1, 100), (2, 98), (4, 96), (8, 94), (16, 0)],
                Result(
                    allow_score_non_ac=True,
                    resource_usage=ResourceUsage(),
                    case_results=[
                        CaseResult(
                            judge_result=JudgeResult.ACCEPTED,
                            message="",
                            absolute_score=99,
                            execution_time=0.0,
                            memory_usage=0,
                        ),
                    ],
                ),
                (2, 2.0, [99]),
                id="5rows_n16_2nd",
            ),
            pytest.param(
                [(1, 100), (2, 98), (4, 96), (8, 94), (16, 0)],
                Result(
                    allow_score_non_ac=True,
                    resource_usage=ResourceUsage(),
                    case_results=[
                        CaseResult(
                            judge_result=JudgeResult.ACCEPTED,
                            message="",
                            absolute_score=98,
                            execution_time=0.0,
                            memory_usage=0,
                        ),
                    ],
                ),
                (2, 2.5, [98]),
                id="5rows_n16_2nd_tie",
            ),
            pytest.param(
                [(1, 100), (2, 98), (4, 96), (8, 94), (16, 0)],
                Result(
                    allow_score_non_ac=True,
                    resource_usage=ResourceUsage(),
                    case_results=[
                        CaseResult(
                            judge_result=JudgeResult.ACCEPTED,
                            message="",
                            absolute_score=97,
                            execution_time=0.0,
                            memory_usage=0,
                        ),
                    ],
                ),
                (4, 4.0, [97]),
                id="5rows_n16_4th",
            ),
            pytest.param(
                [(1, 100), (2, 98), (4, 96), (8, 94), (16, 0)],
                Result(
                    allow_score_non_ac=True,
                    resource_usage=ResourceUsage(),
                    case_results=[
                        CaseResult(
                            judge_result=JudgeResult.ACCEPTED,
                            message="",
                            absolute_score=96,
                            execution_time=0.0,
                            memory_usage=0,
                        ),
                    ],
                ),
                (4, 5.5, [96]),
                id="5rows_n16_4th_tie",
            ),
            pytest.param(
                [(1, 100), (2, 98), (4, 96), (8, 94), (16, 0)],
                Result(
                    allow_score_non_ac=True,
                    resource_usage=ResourceUsage(),
                    case_results=[
                        CaseResult(
                            judge_result=JudgeResult.ACCEPTED,
                            message="",
                            absolute_score=95,
                            execution_time=0.0,
                            memory_usage=0,
                        ),
                    ],
                ),
                (8, 8.0, [95]),
                id="5rows_n16_8th",
            ),
            pytest.param(
                [(1, 100), (2, 98), (4, 96), (8, 94), (16, 0)],
                Result(
                    allow_score_non_ac=True,
                    resource_usage=ResourceUsage(),
                    case_results=[
                        CaseResult(
                            judge_result=JudgeResult.ACCEPTED,
                            message="",
                            absolute_score=94,
                            execution_time=0.0,
                            memory_usage=0,
                        ),
                    ],
                ),
                (8, 11.5, [94]),
                id="5rows_n16_8th_tie",
            ),
            pytest.param(
                [(1, 100), (2, 98), (4, 96), (8, 94), (16, 0)],
                Result(
                    allow_score_non_ac=True,
                    resource_usage=ResourceUsage(),
                    case_results=[
                        CaseResult(
                            judge_result=JudgeResult.ACCEPTED,
                            message="",
                            absolute_score=93,
                            execution_time=0.0,
                            memory_usage=0,
                        ),
                    ],
                ),
                (16, 16.0, [93]),
                id="5rows_n16_16th",
            ),
            pytest.param(
                [(1, 100), (2, 98), (4, 96), (8, 94), (16, 0)],
                Result(
                    allow_score_non_ac=True,
                    resource_usage=ResourceUsage(),
                    case_results=[
                        CaseResult(
                            judge_result=JudgeResult.ACCEPTED,
                            message="",
                            absolute_score=0,
                            execution_time=0.0,
                            memory_usage=0,
                        ),
                    ],
                ),
                (16, 16.0, [0]),
                id="5rows_n16_16th_tie",
            ),
            pytest.param(
                [(idx, 10000 - idx * 100) for idx in list(range(1, 101))],
                Result(
                    allow_score_non_ac=True,
                    resource_usage=ResourceUsage(),
                    case_results=[
                        CaseResult(
                            judge_result=JudgeResult.ACCEPTED,
                            message="",
                            absolute_score=10000,
                            execution_time=0.0,
                            memory_usage=0,
                        ),
                    ],
                ),
                (1, 1.0, [10000]),
                id="100rows_1st",
            ),
            pytest.param(
                [(idx, 10000 - idx * 100) for idx in list(range(1, 101))],
                Result(
                    allow_score_non_ac=True,
                    resource_usage=ResourceUsage(),
                    case_results=[
                        CaseResult(
                            judge_result=JudgeResult.ACCEPTED,
                            message="",
                            absolute_score=9900,
                            execution_time=0.0,
                            memory_usage=0,
                        ),
                    ],
                ),
                (1, 1.0, [9900]),
                id="100rows_1st_tie",
            ),
            pytest.param(
                [(idx, 10000 - idx * 100) for idx in list(range(1, 101))],
                Result(
                    allow_score_non_ac=True,
                    resource_usage=ResourceUsage(),
                    case_results=[
                        CaseResult(
                            judge_result=JudgeResult.ACCEPTED,
                            message="",
                            absolute_score=4134,
                            execution_time=0.0,
                            memory_usage=0,
                        ),
                    ],
                ),
                (59, 59.0, [4134]),
                id="100rows_59th",
            ),
        ],
    )
    def test_get_new_rank_absolute(
        self, standings_scores: list[tuple[int, int]], result: Result, expected: tuple[int, float, list[int]]
    ) -> None:
        standings = Standings(standings_scores=standings_scores)
        assert standings.get_new_rank(result) == expected

    @pytest.mark.parametrize(
        "standings_scores,absolute_scores,relative_score_type,case_scores,expected",
        [
            pytest.param(
                [(1, 150), (1, 150), (3, 125), (4, 75), (5, 0)],
                [[4, 3, 2, 1], [2, 3, 1, 4]],
                RelativeScoreType.MAX,
                [3, 3],
                (1, 1.5, [75, 75]),  # 150(o), 150, 150, 125, 75
                id="max",
            ),
            pytest.param(
                [(1, 144), (2, 138), (3, 131), (4, 125), (5, 0)],
                [[10, 15, 5, 16], [3, 2, 4, 1]],
                RelativeScoreType.MAX,
                [20, 1],
                (1, 2.0, [100, 25]),  # 125(o), 125, 125, 125, 105
                id="max_tie",
            ),
            pytest.param(
                [(1, 150), (1, 150), (3, 125), (4, 75), (5, 0)],
                [[4, 3, 2, 1], [2, 3, 1, 4]],
                RelativeScoreType.MAX,
                [2, 6],
                (1, 1.0, [50, 100]),  # 150(o), 133, 125, 92, 67
                id="max_top",
            ),
            pytest.param(
                [(1, 150), (1, 150), (3, 125), (4, 75), (5, 0)],
                [[4, 3, 2, 1], [2, 3, 1, 4]],
                RelativeScoreType.MAX,
                [1, 5],
                (3, 3.0, [25, 100]),  # 140, 135, 125(o), 105, 70
                id="max_top_partial",
            ),
            pytest.param(
                [(1, 150), (1, 150), (3, 125), (4, 75), (5, 0)],
                [[4, 3, 2, 1], [2, 3, 1, 4]],
                RelativeScoreType.MAX,
                [1, 6],
                (2, 2.0, [25, 100]),  # 133, 125(o), 125, 92, 67
                id="max_top_partial_tie",
            ),
        ],
    )
    def test_get_new_rank_relative(
        self,
        standings_scores: list[tuple[int, int]],
        absolute_scores: list[list[int]],
        relative_score_type: RelativeScoreType,
        case_scores: list[int],
        expected: tuple[int, float, list[int]],
    ) -> None:
        standings = Standings(
            standings_scores=standings_scores,
            relative_results=RelativeResults(
                absolute_scores=absolute_scores,
                relative_score_type=relative_score_type,
                relative_max_score=100,
            ),
        )
        result = Result(
            allow_score_non_ac=True,
            resource_usage=ResourceUsage(),
            case_results=[
                CaseResult(
                    judge_result=JudgeResult.ACCEPTED,
                    message="",
                    absolute_score=case_score,
                    execution_time=0.0,
                    memory_usage=0,
                )
                for case_score in case_scores
            ],
        )
        assert standings.get_new_rank(result) == expected


class TestProblemMetaData:
    @pytest.fixture(scope="class")
    def instantiate_problem_metadata(self, request: pytest.FixtureRequest) -> ProblemMetaData:
        return ProblemMetaData(
            problem_id="ahc001",
            start_at=request.param[0],
            end_at=request.param[1],
            contest_url="https://atcoder.jp/contests/ahc001",
            title="AtCoder Ad",
            problem_type=ProblemType.BATCH,
            score_type=ScoreType.MAXIMIZE,
        )

    @pytest.mark.parametrize(
        "instantiate_problem_metadata,expected",
        [
            pytest.param(
                (dt.datetime(2023, 1, 1, 0, 0, 0), dt.datetime(2023, 1, 1, 6, 0, 0)),
                dt.timedelta(hours=6),
                id="06:00:00",
            ),
            pytest.param(
                (dt.datetime(2023, 1, 1, 0, 0, 0), dt.datetime(2023, 1, 1, 23, 59, 59)),
                dt.timedelta(hours=23, minutes=59, seconds=59),
                id="23:59:59",
            ),
            pytest.param(
                (dt.datetime(2023, 1, 1, 0, 0, 0), dt.datetime(2023, 1, 2, 0, 0, 0)),
                dt.timedelta(days=1),
                id="1day",
            ),
            pytest.param(
                (dt.datetime(2023, 1, 1, 0, 0, 0), dt.datetime(2023, 1, 8, 0, 0, 0)),
                dt.timedelta(weeks=1),
                id="1week",
            ),
            pytest.param(
                (dt.datetime(2023, 1, 1, 0, 0, 0), dt.datetime(2023, 1, 11, 4, 0, 0)),
                dt.timedelta(weeks=1, days=3, hours=4),
                id="10days 4hours",
            ),
        ],
        indirect=["instantiate_problem_metadata"],
    )
    def test_duration(self, instantiate_problem_metadata: ProblemMetaData, expected: dt.timedelta) -> None:
        assert instantiate_problem_metadata.duration == expected

    @pytest.mark.parametrize(
        "instantiate_problem_metadata,expected",
        [
            pytest.param(
                (dt.datetime(2023, 1, 1, 0, 0, 0), dt.datetime(2023, 1, 1, 6, 0, 0)),
                300,
                id="06:00:00",
            ),
            pytest.param(
                (dt.datetime(2023, 1, 1, 0, 0, 0), dt.datetime(2023, 1, 1, 23, 59, 59)),
                300,
                id="23:59:59",
            ),
            pytest.param(
                (dt.datetime(2023, 1, 1, 0, 0, 0), dt.datetime(2023, 1, 2, 0, 0, 0)),
                1800,
                id="1day",
            ),
            pytest.param(
                (dt.datetime(2023, 1, 1, 0, 0, 0), dt.datetime(2023, 1, 8, 0, 0, 0)),
                1800,
                id="1week",
            ),
            pytest.param(
                (dt.datetime(2023, 1, 1, 0, 0, 0), dt.datetime(2023, 1, 11, 4, 0, 0)),
                1800,
                id="10days 4hours",
            ),
        ],
        indirect=["instantiate_problem_metadata"],
    )
    def test_submission_interval_seconds(self, instantiate_problem_metadata: ProblemMetaData, expected: int) -> None:
        assert instantiate_problem_metadata.submission_interval_seconds == expected


@pytest.mark.slow
class TestRatingCalculator:
    @pytest.fixture(scope="class")
    def rating_calculator_instance(self) -> RatingCalculator:
        return RatingCalculator()

    @pytest.mark.parametrize(
        "performances,final_problem_id,context,expected",
        [
            pytest.param(
                {},
                "ahc001",
                pytest.raises(ValueError, match=r"The performances dictionary cannot be empty\."),
                147,
                id="empty",
            ),
            pytest.param(
                {"ahc000": 3200},
                "ahc001",
                pytest.raises(ValueError, match=r"Problem ID ahc000 not found in the contest schedule\."),
                147,
                id="invalid_problem_id",
            ),
            pytest.param(
                {"ahc001": 3200},
                "ahc000",
                pytest.raises(ValueError, match=r"Final contest ahc000 not found in the contest schedule\."),
                0,
                id="invalid_final_problem_id",
            ),
            pytest.param(
                {"ahc045": 1900},
                "ahc045",
                does_not_raise(),
                1050,
                id="first_contest_weight_1",
            ),
            pytest.param(
                {"ahc044": 1900},
                "ahc044",
                does_not_raise(),
                634,
                id="first_contest_weight_0.5",
            ),
            pytest.param(
                {"ahc023": 1711, "ahc026": 1378, "ahc031": 1493, "ahc032": 1546, "ahc035": 1761},
                "ahc044",
                does_not_raise(),
                1407,
                id="ahc044_lyi",
            ),
            pytest.param(
                {"ahc002": 3254, "ahc004": 2119, "ahc028": 2471, "ahc032": 1297, "ahc035": 1446},
                "ahc044",
                does_not_raise(),
                2211,
                id="ahc044_tourist",
            ),
            pytest.param(
                {"ahc001": 1735, "ahc002": 2763, "ahc028": 1870, "ahc042": 2267, "ahc044": 2204},
                "ahc044",
                does_not_raise(),
                1900,
                id="ahc044_snuke",
            ),
            pytest.param(
                {
                    "ahc010": 1338,
                    "ahc012": 2399,
                    "ahc020": 2531,
                    "ahc021": 2789,
                    "ahc026": 2269,
                    "ahc029": 2882,
                    "ahc028": 2875,
                    "ahc032": 2345,
                    "ahc034": 2377,
                    "ahc037": 2017,
                    "ahc039": 3140,
                    "ahc040": 3459,
                    "ahc041": 2443,
                    "ahc042": 2549,
                },
                "ahc044",
                does_not_raise(),
                2972,
                id="ahc044_chokudai",
            ),
            pytest.param(
                {
                    "ahc001": 2023,
                    "ahc002": 1317,
                    "ahc003": 2243,
                    "ahc004": 2354,
                    "ahc005": 1403,
                    "rcl-contest-2021-long": 2381,
                    "future-contest-2022-qual": 990,
                    "ahc006": 2096,
                    "ahc007": 2129,
                    "ahc008": 2375,
                    "ahc009": 1682,
                    "ahc010": 1945,
                    "ahc011": 2441,
                    "ahc012": 1190,
                    "ahc013": 1790,
                    "ahc014": 2674,
                    "ahc015": 3506,
                    "ahc016": 2650,
                    "ahc017": 2747,
                    "ahc018": 2650,
                    "ahc019": 2025,
                    "ahc020": 2459,
                    "ahc021": 1971,
                    "ahc022": 2604,
                    "toyota2023summer-final": 2667,
                    "ahc023": 2466,
                    "ahc024": 2265,
                    "ahc025": 3479,
                    "ahc026": 2211,
                    "ahc027": 3139,
                    "ahc028": 2587,
                    "ahc029": 3392,
                    "ahc030": 3104,
                    "ahc031": 1631,
                    "ahc033": 3110,
                    "ahc034": 1854,
                    "ahc035": 2072,
                    "ahc036": 2130,
                    "ahc037": 2132,
                    "ahc040": 1692,
                    "ahc041": 2964,
                    "ahc042": 2412,
                    "ahc043": 2662,
                    "ahc044": 2467,
                },
                "ahc044",
                does_not_raise(),
                3176,
                id="ahc044_eijirou",
            ),
        ],
    )
    def test_calculate_rating(
        self,
        performances: dict[str, int],
        final_problem_id: str,
        context: AbstractContextManager[None],
        expected: int,
        rating_calculator_instance: RatingCalculator,
    ) -> None:
        with context:
            assert rating_calculator_instance.calculate_rating(performances, final_problem_id) == expected


@pytest.mark.slow
class TestRankingCalculator:
    @pytest.fixture(scope="class")
    def ranking_calculator_instance(self) -> RankingCalculator:
        return RankingCalculator(minimum_participation=0)

    @pytest.mark.slow
    @pytest.mark.parametrize(
        "minimum_participation,expected",
        [
            pytest.param(0, 6139, id="minimum_participation_0"),
            pytest.param(5, 2220, id="minimum_participation_5"),
        ],
    )
    def test_num_active_users(self, minimum_participation: int, expected: int) -> None:
        assert RankingCalculator(minimum_participation=minimum_participation).num_active_users == expected

    @pytest.mark.slow
    @pytest.mark.parametrize(
        "rating,context,expected",
        [
            pytest.param(3348, does_not_raise(), 1, id="1st"),
            pytest.param(3347, does_not_raise(), 1, id="1st_tie"),
            pytest.param(3263, does_not_raise(), 2, id="2nd"),
            pytest.param(1396, does_not_raise(), 1092, id="1092th_tie"),
            pytest.param(1392, does_not_raise(), 1102, id="1102th"),
            pytest.param(194, does_not_raise(), 3773, id="3773th_tie"),
            pytest.param(5, does_not_raise(), 6128, id="last_entry"),
            pytest.param(4, does_not_raise(), 6140, id="worst"),
            pytest.param(0, does_not_raise(), 6140, id="zero"),
            pytest.param(
                -1, pytest.raises(ValueError, match=r"The rating must be greater than or equal to 0\."), 0, id="invalid"
            ),
        ],
    )
    def test_calculate_rating_rank(
        self,
        rating: int,
        context: AbstractContextManager[None],
        expected: int,
        ranking_calculator_instance: RankingCalculator,
    ) -> None:
        with context:
            assert ranking_calculator_instance.calculate_rating_rank(rating) == expected

    @pytest.mark.slow
    @pytest.mark.parametrize(
        "rank,method,context,expected",
        [
            pytest.param(1, "original", does_not_raise(), 100.0 * 1.0 / 6139, id="1st_original"),
            pytest.param(1, "hazen", does_not_raise(), 100.0 * 0.5 / 6140, id="1st_hazen"),
            pytest.param(1, "weibull", does_not_raise(), 100.0 * 1.0 / 6141, id="1st_weibull"),
            pytest.param(150, "original", does_not_raise(), 100.0 * 150.0 / 6139, id="150th_original"),
            pytest.param(150, "hazen", does_not_raise(), 100.0 * 149.5 / 6140, id="150th_hazen"),
            pytest.param(150, "weibull", does_not_raise(), 100.0 * 150.0 / 6141, id="150th_weibull"),
            pytest.param(6139, "original", does_not_raise(), 100.0, id="6139th_original"),
            pytest.param(6139, "hazen", does_not_raise(), 100.0 * 6138.5 / 6140, id="6139th_hazen"),
            pytest.param(6139, "weibull", does_not_raise(), 100.0 * 6139.0 / 6141, id="6139th_weibull"),
            pytest.param(6140, "original", does_not_raise(), 100.0, id="6140th_original"),
            pytest.param(6140, "hazen", does_not_raise(), 100.0 * 6139.5 / 6140, id="6140th_hazen"),
            pytest.param(6140, "weibull", does_not_raise(), 100.0 * 6140.0 / 6141, id="6140th_weibull"),
            pytest.param(
                0,
                "original",
                pytest.raises(ValueError, match=r"The rank must be between 1 and 6140 \(the number of users \+ 1\)\."),
                0.0,
                id="invalid_rank_0th_original",
            ),
            pytest.param(
                0,
                "hazen",
                pytest.raises(ValueError, match=r"The rank must be between 1 and 6140 \(the number of users \+ 1\)\."),
                0.0,
                id="invalid_rank_0th_hazen",
            ),
            pytest.param(
                0,
                "weibull",
                pytest.raises(ValueError, match=r"The rank must be between 1 and 6140 \(the number of users \+ 1\)\."),
                0.0,
                id="invalid_rank_0th_weibull",
            ),
            pytest.param(
                6141,
                "original",
                pytest.raises(ValueError, match=r"The rank must be between 1 and 6140 \(the number of users \+ 1\)\."),
                0.0,
                id="invalid_rank_6141st_original",
            ),
            pytest.param(
                6141,
                "hazen",
                pytest.raises(ValueError, match=r"The rank must be between 1 and 6140 \(the number of users \+ 1\)\."),
                0.0,
                id="invalid_rank_6141st_hazen",
            ),
            pytest.param(
                6141,
                "weibull",
                pytest.raises(ValueError, match=r"The rank must be between 1 and 6140 \(the number of users \+ 1\)\."),
                0.0,
                id="invalid_rank_6141st_weibull",
            ),
            pytest.param(
                3070,
                "hoge",
                pytest.raises(
                    ValueError,
                    match=r"Invalid method: hoge\. Supported methods are 'original', 'hazen', and 'weibull'\.",
                ),
                0.0,
                id="invalid_method",
            ),
        ],
    )
    def test_convert_rank_to_percentile(
        self,
        rank: int,
        method: str,
        context: AbstractContextManager[None],
        expected: float,
        ranking_calculator_instance: RankingCalculator,
    ) -> None:
        with context:
            assert ranking_calculator_instance.convert_rank_to_percentile(rank, method) == pytest.approx(expected)
