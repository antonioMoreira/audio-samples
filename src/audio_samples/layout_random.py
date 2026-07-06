import random
from typing import List, Tuple, Optional
from audio_samples.rules import ChunksRule
from audio_samples.feasibility import normalize_intervals

def generate_random_layout(
    duration: float,
    rule: ChunksRule,
    global_remove_seconds: Optional[List[Tuple[int, int]]] = None,
    seed: Optional[int] = None
) -> List[Tuple[int, int]]:
    """Generates disjoint random chunk boundaries respecting exclusions.

    Args:
        duration: Total audio duration in seconds.
        rule: The rule defining chunk size, amount, and custom exclusions.
        global_remove_seconds: Global exclusion ranges.
        seed: Random seed for reproducibility.

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
    chunks: List[Tuple[int, int]] = []
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

        # Check overlap with already selected chunks
        overlaps_chunk = False
        for c_start, c_end in chunks:
            if max(start, c_start) < min(end, c_end):
                overlaps_chunk = True
                break

        if overlaps_chunk:
            attempts += 1
            continue

        chunks.append((start, end))

    chunks.sort(key=lambda x: x[0])
    return chunks
