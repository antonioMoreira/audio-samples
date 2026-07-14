from audio_samples.rules import ChunksRule


def normalize_intervals(
    intervals: list[tuple[int, int]], duration: float
) -> list[tuple[int, int]]:
    """Caps, sorts, and merges overlapping or adjacent time intervals."""
    if not intervals:
        return []

    capped = []
    for start, end in intervals:
        # Cap to [0, duration]
        s = max(0, min(start, int(duration)))
        e = max(0, min(end, int(duration)))
        if s < e:
            capped.append((s, e))

    if not capped:
        return []

    # Sort by start time
    capped.sort(key=lambda x: x[0])

    merged = [capped[0]]
    for current_start, current_end in capped[1:]:
        last_start, last_end = merged[-1]
        if current_start <= last_end:
            # Overlap or adjacent -> merge
            merged[-1] = (last_start, max(last_end, current_end))
        else:
            merged.append((current_start, current_end))

    return merged


def calculate_available_duration(
    duration: float, normalized_intervals: list[tuple[int, int]]
) -> float:
    """Calculates available duration after subtracting normalized excluded intervals."""
    total_removed = sum(end - start for start, end in normalized_intervals)
    return max(0.0, float(duration) - float(total_removed))


def check_feasibility(
    duration: float,
    rules: list[ChunksRule],
    sampling_rule: str,
    remove_seconds: list[tuple[int, int]] | None = None,
) -> None:
    """Verifies that all chunking rules can be satisfied given the audio duration.

    Raises ValueError with a descriptive message if feasibility cannot be satisfied.
    """
    for rule in rules:
        # Combine global remove_seconds and rule-specific remove_seconds
        combined_remove = []
        if remove_seconds:
            combined_remove.extend(remove_seconds)
        if rule.remove_seconds:
            combined_remove.extend(rule.remove_seconds)

        normalized = normalize_intervals(combined_remove, duration)
        available_dur = calculate_available_duration(duration, normalized)

        # 1. Mutually exclusive Random + amount = -1
        if sampling_rule.lower() == "random" and rule.amount == -1:
            raise ValueError("amount=-1 and Random are mutually exclusive")

        # 2. Check chunk size vs available duration
        if rule.chunk_size_seconds > available_dur:
            raise ValueError(
                f"Chunk size {rule.chunk_size_seconds}s is larger than "
                f"total available duration {available_dur}s for this rule."
            )

        # 3. Check requested total duration vs available duration for individual rule
        if rule.amount > 0:
            requested_dur = rule.amount * rule.chunk_size_seconds
            if requested_dur > available_dur:
                raise ValueError(
                    f"Requested duration {requested_dur}s "
                    f"({rule.amount} chunks of {rule.chunk_size_seconds}s) "
                    f"exceeds available duration {available_dur}s."
                )

        # 4. Check if continuous layout cannot fit the requested amount
        if sampling_rule.lower() == "continuous" and rule.amount > 0:
            current_time = 0
            chunks_count = 0
            while current_time + rule.chunk_size_seconds <= int(duration):
                if chunks_count >= rule.amount:
                    break

                candidate_start = current_time
                candidate_end = current_time + rule.chunk_size_seconds

                overlap_found = False
                for ex_start, ex_end in normalized:
                    if max(candidate_start, ex_start) < min(candidate_end, ex_end):
                        overlap_found = True
                        current_time = ex_end
                        break

                if not overlap_found:
                    chunks_count += 1
                    current_time = candidate_end

            if chunks_count < rule.amount:
                raise ValueError(
                    "Continuous layout cannot fit the requested amount of "
                    f"{rule.amount} chunks of size {rule.chunk_size_seconds}s "
                    f"(only {chunks_count} can fit)."
                )

    # 5. Check cumulative requested duration vs global available duration
    global_normalized = normalize_intervals(remove_seconds or [], duration)
    global_available_dur = calculate_available_duration(duration, global_normalized)

    total_requested_dur = sum(
        rule.amount * rule.chunk_size_seconds for rule in rules if rule.amount > 0
    )
    if total_requested_dur > global_available_dur:
        raise ValueError(
            f"Cumulative requested duration {total_requested_dur}s exceeds "
            f"available duration {global_available_dur}s."
        )
