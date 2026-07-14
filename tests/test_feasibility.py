import pytest

from audio_samples.feasibility import (
    calculate_available_duration,
    check_feasibility,
    normalize_intervals,
)
from audio_samples.rules import ChunksRule


def test_normalize_intervals():
    # Empty intervals
    assert normalize_intervals([], 100) == []

    # Simple bounds and ordering
    assert normalize_intervals([(10, 20), (5, 15)], 100) == [(5, 20)]

    # Out of bounds capping
    assert normalize_intervals([(-5, 10), (90, 110)], 100) == [(0, 10), (90, 100)]

    # Adjacent merging
    assert normalize_intervals([(10, 20), (20, 30)], 100) == [(10, 30)]


def test_calculate_available_duration():
    assert calculate_available_duration(100, []) == 100.0
    assert calculate_available_duration(100, [(10, 20), (30, 45)]) == 75.0
    assert calculate_available_duration(100, [(0, 110)]) == 0.0


def test_check_feasibility_happy_continuous():
    rules = [
        ChunksRule(chunk_size_seconds=10, amount=5),
        ChunksRule(chunk_size_seconds=30, amount=-1),
    ]
    # 100s duration, no removed intervals -> available is 100
    # continuous 10s * 5 = 50 <= 100 -> ok
    # continuous 30s * -1 -> ok (at least one 30s fits)
    check_feasibility(100, rules, "Continuous")


def test_check_feasibility_happy_random():
    rules = [
        ChunksRule(chunk_size_seconds=10, amount=3),
        ChunksRule(chunk_size_seconds=5, amount=8),
    ]
    # 100s duration, remove 10-20 (available = 90)
    # 10*3 = 30 <= 90 -> ok
    # 5*8 = 40 <= 90 -> ok
    check_feasibility(100, rules, "Random", remove_seconds=[(10, 20)])


def test_check_feasibility_random_infinite_amount_error():
    rules = [ChunksRule(chunk_size_seconds=10, amount=-1)]
    with pytest.raises(ValueError, match="amount=-1 and Random are mutually exclusive"):
        check_feasibility(100, rules, "Random")


def test_check_feasibility_insufficient_duration():
    rules = [ChunksRule(chunk_size_seconds=10, amount=11)]
    with pytest.raises(
        ValueError, match=r"Requested duration .* exceeds available duration"
    ):
        check_feasibility(100, rules, "Continuous")


def test_check_feasibility_single_chunk_larger_than_duration():
    rules = [ChunksRule(chunk_size_seconds=110, amount=1)]
    with pytest.raises(
        ValueError, match=r"Chunk size .* is larger than total available duration"
    ):
        check_feasibility(100, rules, "Continuous")


def test_check_feasibility_cumulative_insufficient_duration():
    rules = [
        ChunksRule(chunk_size_seconds=10, amount=6),
        ChunksRule(chunk_size_seconds=20, amount=3),
    ]
    # Total requested = (10 * 6) + (20 * 3) = 120s, but only 100s available.
    with pytest.raises(
        ValueError,
        match=r"Cumulative requested duration 120s exceeds available duration 100\.0s",
    ):
        check_feasibility(100, rules, "Random")


def test_check_feasibility_continuous_cannot_fit_due_to_exclusions():
    rules = [ChunksRule(chunk_size_seconds=10, amount=1)]
    # Duration is 30. But with remove_seconds=[(8, 22)], segments are
    # [0, 8] and [22, 30]. Neither segment is large enough to fit a
    # 10s chunk, even though available duration is 16s.
    # Total fit = 0. Requested amount = 1.
    with pytest.raises(
        ValueError,
        match="Continuous layout cannot fit the requested amount of 1 chunks",
    ):
        check_feasibility(30, rules, "Continuous", remove_seconds=[(8, 22)])
