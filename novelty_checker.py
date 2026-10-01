import re
from difflib import SequenceMatcher


def _tokens(text: str) -> list[str]:
    return re.findall(r"[a-z0-9_]+", text.casefold())


def check_novelty(
    generated_text: str,
    source_text: str,
    threshold: float = 0.78,
) -> dict:
    generated_tokens = _tokens(generated_text)
    source_tokens = _tokens(source_text)
    if not generated_tokens or not source_tokens:
        return {"is_novel": True, "score": 0.0, "threshold": threshold}

    generated_normalized = " ".join(generated_tokens)
    source_normalized = " ".join(source_tokens)
    sequence_score = SequenceMatcher(
        None, generated_normalized, source_normalized, autojunk=False
    ).ratio()

    source_vocabulary = set(source_tokens)
    containment_score = sum(
        token in source_vocabulary for token in generated_tokens
    ) / len(generated_tokens)
    score = round(max(sequence_score, containment_score), 4)
    return {
        "is_novel": score < threshold,
        "score": score,
        "threshold": threshold,
        "sequence_score": round(sequence_score, 4),
        "containment_score": round(containment_score, 4),
    }
