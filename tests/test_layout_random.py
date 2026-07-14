import pytest

from audio_samples.layout_random import generate_random_layout
from audio_samples.rules import ChunksRule


def test_generate_random_layout_happy():
    rule = ChunksRule(chunk_size_seconds=5, amount=3)
    chunks = generate_random_layout(100.0, rule, seed=42)
    assert len(chunks) == 3

    # Verify each is 5 seconds long
    for start, end in chunks:
        assert end - start == 5

    # Verify disjointness
    for i, (s1, e1) in enumerate(chunks):
        for j, (s2, e2) in enumerate(chunks):
            if i != j:
                assert max(s1, s2) >= min(e1, e2), (
                    f"Chunks {s1}-{e1} and {s2}-{e2} overlap!"
                )


def test_generate_random_layout_deterministic_with_seed():
    rule = ChunksRule(chunk_size_seconds=10, amount=2)
    chunks1 = generate_random_layout(60.0, rule, seed=123)
    chunks2 = generate_random_layout(60.0, rule, seed=123)
    assert chunks1 == chunks2


def test_generate_random_layout_exclusions():
    # Exclusion covers [10, 50], total duration 60.
    # Placing two 5s chunks, they must fall into [0, 10] or [50, 60]
    rule = ChunksRule(chunk_size_seconds=5, amount=2, remove_seconds=[(10, 50)])
    chunks = generate_random_layout(60.0, rule, seed=777)
    assert len(chunks) == 2

    for start, end in chunks:
        # Check they do not overlap with [10, 50]
        assert max(start, 10) >= min(end, 50)


def test_generate_random_layout_unsupported_unlimited():
    rule = ChunksRule(chunk_size_seconds=5, amount=-1)
    with pytest.raises(ValueError, match="amount=-1 and Random are mutually exclusive"):
        generate_random_layout(100.0, rule)


def test_generate_random_layout_failure_to_place():
    # Try to place three 10s chunks in 20s audio -> impossible to be disjoint
    rule = ChunksRule(chunk_size_seconds=10, amount=3)
    with pytest.raises(ValueError, match="Failed to place 3 disjoint chunks"):
        generate_random_layout(20.0, rule)


def test_generate_random_layout_with_existing_chunks():
    # Total duration 30s. We have existing chunks [(0, 10), (20, 30)].
    # Placing a 10s chunk should only be possible at [10, 20].
    rule = ChunksRule(chunk_size_seconds=10, amount=1)
    existing = [(0, 10), (20, 30)]
    chunks = generate_random_layout(30.0, rule, existing_chunks=existing, seed=42)
    assert len(chunks) == 1
    assert chunks[0] == (10, 20)
