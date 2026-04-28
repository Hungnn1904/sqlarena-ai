from __future__ import annotations

import json

from pydantic import BaseModel, field_validator


class QuestionBlueprint(BaseModel):
    intent: str
    target_skill: str
    schema_tables: list[str]
    trap_strategy: str
    ambiguity_risk: str
    difficulty: str

    @field_validator("ambiguity_risk")
    @classmethod
    def validate_ambiguity_risk(cls, v: str) -> str:
        allowed = {"low", "medium", "high"}
        if v.lower() not in allowed:
            raise ValueError(f"ambiguity_risk must be one of {allowed}, got '{v}'")
        return v.lower()

    @field_validator("difficulty")
    @classmethod
    def validate_difficulty(cls, v: str) -> str:
        allowed = {"easy", "medium", "hard"}
        if v.lower() not in allowed:
            raise ValueError(f"difficulty must be one of {allowed}, got '{v}'")
        return v.lower()

    @field_validator("schema_tables")
    @classmethod
    def validate_tables_non_empty(cls, v: list[str]) -> list[str]:
        if not v:
            raise ValueError("schema_tables must contain at least one table")
        return v


def _build_schema_summary(schema: dict) -> str:
    lines = []
    for table, defn in schema.get("tables", {}).items():
        cols = ", ".join(defn.get("columns", {}).keys())
        lines.append(f"  {table}({cols})")
    return "\n".join(lines)


def _build_prompt(difficulty: str, topic: str, schema: dict) -> str:
    schema_summary = _build_schema_summary(schema)
    table_names = list(schema.get("tables", {}).keys())

    return f"""You are an SQL question design expert. Generate a question blueprint as JSON.

Schema:
{schema_summary}

Available tables: {table_names}
Target difficulty: {difficulty}
Target SQL skill: {topic}

Return ONLY valid JSON matching this exact structure:
{{
  "intent": "<one sentence describing what the question asks the user to find>",
  "target_skill": "<SQL skill being tested, e.g. SUBQUERY>",
  "schema_tables": ["<table1>", "<table2>"],
  "trap_strategy": "<describe one common mistake or edge case the question should expose>",
  "ambiguity_risk": "<low | medium | high>",
  "difficulty": "{difficulty}"
}}

Rules:
- intent must be a clear, specific task (not generic)
- schema_tables must only contain tables from the available list above
- trap_strategy must be specific to the chosen tables and skill
- Do not include any text outside the JSON object
- Do not use markdown code fences"""


def _extract_json(raw: str) -> str:
    raw = raw.strip()
    if raw.startswith("```"):
        lines = raw.splitlines()
        inner = []
        inside = False
        for line in lines:
            if line.startswith("```") and not inside:
                inside = True
                continue
            if line.startswith("```") and inside:
                break
            if inside:
                inner.append(line)
        raw = "\n".join(inner).strip()
    brace_start = raw.find("{")
    brace_end = raw.rfind("}")
    if brace_start == -1 or brace_end == -1:
        raise ValueError("No JSON object found in LLM output")
    return raw[brace_start: brace_end + 1]


def plan_question(difficulty: str, topic: str, schema: dict, llm) -> QuestionBlueprint:
    difficulty = difficulty.lower()
    if difficulty not in {"easy", "medium", "hard"}:
        raise ValueError(f"Invalid difficulty '{difficulty}'")

    prompt = _build_prompt(difficulty, topic, schema)

    raw_output = llm.generate("question_planning", prompt)

    if not raw_output or not raw_output.strip():
        raise ValueError("LLM returned empty output for question planning")

    json_str = _extract_json(raw_output)

    try:
        data = json.loads(json_str)
    except json.JSONDecodeError as exc:
        raise ValueError(
            f"Failed to parse LLM output as JSON: {exc}\nRaw output:\n{raw_output[:500]}"
        ) from exc

    available_tables = set(schema.get("tables", {}).keys())
    if "schema_tables" in data and isinstance(data["schema_tables"], list):
        invalid = [t for t in data["schema_tables"] if t not in available_tables]
        if invalid:
            data["schema_tables"] = [t for t in data["schema_tables"] if t in available_tables]
            if not data["schema_tables"]:
                data["schema_tables"] = [next(iter(available_tables))]

    try:
        blueprint = QuestionBlueprint(**data)
    except Exception as exc:
        raise ValueError(
            f"LLM JSON does not match QuestionBlueprint schema: {exc}\nParsed data: {data}"
        ) from exc

    return blueprint
