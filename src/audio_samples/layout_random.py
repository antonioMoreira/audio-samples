import random

from audio_samples.feasibility import normalize_intervals
from audio_samples.rules import ChunksRule


def generate_random_layout(
    duration: float,
    rule: ChunksRule,
    global_remove_seconds: list[tuple[int, int]] | None = None,
    seed: int | None = None,
    existing_chunks: list[tuple[int, int]] | None = None,
) -> list[tuple[int, int]]:
    """Generates disjoint random chunk boundaries respecting exclusions.

    Args:
        duration: Total audio duration in seconds.
        rule: The rule defining chunk size, amount, and custom exclusions.
        global_remove_seconds: Global exclusion ranges.
        seed: Random seed for reproducibility.
        existing_chunks: Chunks from other rules to avoid overlaps.

    Returns:
        A sorted list of chunk boundaries as (start_second, end_second) tuples.

    Raises:
        ValueError: If amount = -1 (not allowed for random), or if placement
                    fails after 1000 retry attempts.
    """
    if rule.amount == -1:
        raise ValueError("amount=-1 and Random are mutually exclusive")
    if rule.amount <= 0:
        raise ValueError("chunk amount must be positive for Random sampling")

    combined_remove = []
    if global_remove_seconds:
        combined_remove.extend(global_remove_seconds)
    if rule.remove_seconds:
        combined_remove.extend(rule.remove_seconds)

    normalized = normalize_intervals(combined_remove, duration)

    rng = random.Random(seed)
    chunks: list[tuple[int, int]] = []
    chunk_size = rule.chunk_size_seconds
    amount = rule.amount

    max_start = int(duration) - chunk_size
    if max_start < 0:
        raise ValueError(
            f"Chunk size {chunk_size}s is larger than total duration {duration}s."
        )

    attempts = 0
    max_attempts = 1000

    while len(chunks) < amount:
        if attempts >= max_attempts:
            raise ValueError(
                f"Failed to place {amount} disjoint chunks of size {chunk_size}s "
                f"after {max_attempts} attempts."
            )

        start = rng.randint(0, max_start)
        end = start + chunk_size

        # Check overlap with remove_seconds
        overlaps_remove = False
        for r_start, r_end in normalized:
            if max(start, r_start) < min(end, r_end):
                overlaps_remove = True
                break

        if overlaps_remove:
            attempts += 1
            continue

        # Check overlap with already selected chunks in current rule
        overlaps_chunk = False
        for c_start, c_end in chunks:
            if max(start, c_start) < min(end, c_end):
                overlaps_chunk = True
                break

        if overlaps_chunk:
            attempts += 1
            continue

        # Check overlap with existing chunks from other rules
        if existing_chunks:
            for c_start, c_end in existing_chunks:
                if max(start, c_start) < min(end, c_end):
                    overlaps_chunk = True
                    break

        if overlaps_chunk:
            attempts += 1
            continue

        chunks.append((start, end))

    chunks.sort(key=lambda x: x[0])
    return chunks
