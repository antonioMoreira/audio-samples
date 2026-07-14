from audio_samples.layout_continuous import generate_continuous_layout
from audio_samples.rules import ChunksRule


def test_generate_continuous_layout_simple():
    rule = ChunksRule(chunk_size_seconds=10, amount=3)
    # duration 35, should place at 0-10, 10-20, 20-30
    chunks = generate_continuous_layout(35.0, rule)
    assert chunks == [(0, 10), (10, 20), (20, 30)]


def test_generate_continuous_layout_unlimited():
    rule = ChunksRule(chunk_size_seconds=15, amount=-1)
    # duration 50, should place at 0-15, 15-30, 30-45
    chunks = generate_continuous_layout(50.0, rule)
    assert chunks == [(0, 15), (15, 30), (30, 45)]


def test_generate_continuous_layout_with_exclusions():
    rule = ChunksRule(chunk_size_seconds=15, amount=-1, remove_seconds=[(10, 20)])
    # duration 60, should skip [0, 10] (too small), skip [10, 20],
    # place [20, 35], [35, 50]
    chunks = generate_continuous_layout(60.0, rule)
    assert chunks == [(20, 35), (35, 50)]


def test_generate_continuous_layout_with_global_and_rule_exclusions():
    rule = ChunksRule(chunk_size_seconds=10, amount=-1, remove_seconds=[(40, 50)])
    global_remove = [(15, 25)]
    # duration 60
    # normalized: (15, 25), (40, 50)
    # 0-10: fits -> [(0, 10)]
    # 10-20: overlaps with (15, 25) -> current_time set to 25
    # 25-35: fits -> [(0, 10), (25, 35)]
    # 35-45: overlaps with (40, 50) -> current_time set to 50
    # 50-60: fits -> [(0, 10), (25, 35), (50, 60)]
    chunks = generate_continuous_layout(
        60.0, rule, global_remove_seconds=global_remove
    )
    assert chunks == [(0, 10), (25, 35), (50, 60)]


def test_generate_continuous_layout_too_large():
    rule = ChunksRule(chunk_size_seconds=40, amount=1)
    chunks = generate_continuous_layout(30.0, rule)
    assert chunks == []
