"""
retry_policy.py — Retry strategies for question generation pipeline.
"""

_RELAXED_PREFIX = (
    "The previous attempt was too complex or failed validation. "
    "Please generate a SIMPLER version: avoid subqueries, CTEs, window functions, "
    "and trap strategies. Use straightforward SELECT with basic WHERE/GROUP BY only."
)

_MINIMAL_PREFIX = (
    "Generate the SIMPLEST possible SQL question about this topic. "
    "Single table, single condition, no joins. "
    "The question must be answerable by a beginner-level SQL student."
)


def get_retry_prompt(original_prompt: str, attempt: int, difficulty: str, topic: str) -> str:
    """
    Returns a modified prompt based on retry attempt number.

    attempt 1 → original prompt unchanged (caller retries as-is)
    attempt 2 → relaxed: strip complexity hints, prepend simplification instruction
    attempt 3 → minimal: override entirely to simplest possible question for topic
    """
    if attempt <= 1:
        return original_prompt

    if attempt == 2:
        return f"{_RELAXED_PREFIX}\n\nOriginal task (difficulty={difficulty}, topic={topic}):\n{original_prompt}"

    # attempt >= 3 → minimal
    return (
        f"{_MINIMAL_PREFIX}\n\n"
        f"Topic: {topic}\n"
        f"Difficulty target: {difficulty} (but keep it as simple as possible)\n\n"
        f"{original_prompt}"
    )


def should_use_archive(attempt: int, max_retries: int = 3) -> bool:
    """
    Returns True when all retries are exhausted and we should fall back
    to a pre-approved archived question instead of generating a new one.
    """
    return attempt > max_retries
