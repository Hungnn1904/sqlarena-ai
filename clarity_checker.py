from __future__ import annotations

import re

_ACTION_WORDS = frozenset([
    "find", "list", "show", "count", "get", "calculate", "display",
    "return", "retrieve", "select", "fetch", "report", "identify",
])

_AMBIGUOUS_PRONOUNS = re.compile(
    r"\b(it|they|them|their|those|these)\b",
    re.IGNORECASE,
)

_PRONOUN_ANTECEDENTS = re.compile(
    r"\b(employees?|departments?|products?|sales?|inventory|records?|"
    r"rows?|tables?|data|results?|values?|items?)\b",
    re.IGNORECASE,
)

_CONTRADICTORY_PAIRS = [
    (r"\ball\b", r"\bsome\b"),
    (r"\bminimum\b", r"\bmaximum\b"),
    (r"\bmin\b", r"\bmax\b"),
    (r"\binclude\b", r"\bexclude\b"),
    (r"\bwith\b.*?\bwithout\b", None),
]

_MIN_CHARS = 20
_ISSUE_PENALTY = 0.25


def _has_action_word(text: str) -> bool:
    words = re.findall(r"\b\w+\b", text.lower())
    return any(w in _ACTION_WORDS for w in words)


def _has_unresolved_pronouns(text: str) -> bool:
    pronouns = _AMBIGUOUS_PRONOUNS.findall(text)
    if not pronouns:
        return False
    antecedents = _PRONOUN_ANTECEDENTS.findall(text)
    return len(pronouns) > 0 and len(antecedents) == 0


def _has_contradictory_terms(text: str) -> list[str]:
    found = []
    lower = text.lower()
    for pair in _CONTRADICTORY_PAIRS:
        if pair[1] is None:
            if re.search(pair[0], lower):
                found.append(f"contradictory pattern: '{pair[0]}'")
        else:
            if re.search(pair[0], lower) and re.search(pair[1], lower):
                pat_a = pair[0].replace(r"\b", "").replace("\\", "")
                pat_b = pair[1].replace(r"\b", "").replace("\\", "")
                found.append(f"contradictory terms: '{pat_a}' and '{pat_b}'")
    return found


def check_clarity(question_text: str) -> dict:
    if not isinstance(question_text, str):
        return {
            "is_clear": False,
            "score": 0.0,
            "issues": ["Input is not a string"],
        }

    issues: list[str] = []
    stripped = question_text.strip()

    if not stripped:
        return {"is_clear": False, "score": 0.0, "issues": ["Question is empty"]}

    if len(stripped) < _MIN_CHARS:
        issues.append(f"Question too short (minimum {_MIN_CHARS} characters)")

    if not _has_action_word(stripped):
        issues.append(
            "Missing action word (expected one of: find, list, show, count, get, "
            "calculate, display, return, retrieve)"
        )

    if _has_unresolved_pronouns(stripped):
        issues.append(
            "Ambiguous pronoun used (e.g. 'it', 'they') without a clear antecedent noun"
        )

    contradictions = _has_contradictory_terms(stripped)
    for c in contradictions:
        issues.append(f"Potential contradiction: {c}")

    raw_score = 1.0 - len(issues) * _ISSUE_PENALTY
    score = max(0.0, min(1.0, raw_score))
    is_clear = len(issues) == 0

    return {
        "is_clear": is_clear,
        "score": round(score, 2),
        "issues": issues,
    }
