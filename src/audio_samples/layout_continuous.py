from audio_samples.feasibility import normalize_intervals
from audio_samples.rules import ChunksRule


def generate_continuous_layout(
    duration: float,
    rule: ChunksRule,
    global_remove_seconds: list[tuple[int, int]] | None = None,
) -> list[tuple[int, int]]:
    """Generates continuous (sequential) chunk boundaries respecting exclusions.

    Args:
        duration: Total audio duration in seconds.
        rule: The rule defining chunk size, amount, and custom exclusions.
        global_remove_seconds: Global exclusion ranges.

    Returns:
        A list of chunk boundaries as (start_second, end_second) tuples.
    """
    combined_remove = []
    if global_remove_seconds:
        combined_remove.extend(global_remove_seconds)
    if rule.remove_seconds:
        combined_remove.extend(rule.remove_seconds)

    normalized = normalize_intervals(combined_remove, duration)

    chunks = []
    chunk_size = rule.chunk_size_seconds
    amount = rule.amount

    current_time = 0
    while current_time + chunk_size <= int(duration):
        if amount != -1 and len(chunks) >= amount:
            break

        candidate_start = current_time
        candidate_end = current_time + chunk_size

        overlap_found = False
        for ex_start, ex_end in normalized:
            if max(candidate_start, ex_start) < min(candidate_end, ex_end):
                overlap_found = True
                current_time = ex_end
                break

        if not overlap_found:
            chunks.append((candidate_start, candidate_end))
            current_time = candidate_end

    return chunks
