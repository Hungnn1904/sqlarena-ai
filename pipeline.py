"""
pipeline.py — 7-step SQL question generation pipeline (plain Python, no cloud dependency).
"""

import json
import logging
import os

from dotenv import load_dotenv

from clarity_checker import check_clarity
from execution_engine import verify_in_sandbox
from llm_gateway import LLMGateway
from question_bank import QuestionBank
from question_planner import QuestionBlueprint, plan_question
from retry_policy import get_retry_prompt, should_use_archive
from schema_loader import generate_ddl, generate_seed, load_schema
from taxonomy import get_difficulty_config, get_few_shot_example, get_topic_pool

load_dotenv(override=True)

logger = logging.getLogger(__name__)

_GENERATOR_PROMPT = """You are an expert SQL question author.

Database schema (DDL):
{schema_sql}

Question blueprint:
- Difficulty: {difficulty}
- Topic: {topic}
- Required SQL constructs: {constructs}
- Trap strategy: {trap_strategy}

Few-shot example:
{few_shot}

Seed data available:
{seed_sql}

Generate ONE SQL exam question that matches the blueprint exactly.

Return ONLY this JSON object:
{{
  "question_text": "<clear exam-style question for students>",
  "schema_sql": "<full CREATE TABLE statements needed>",
  "seed_sql": "<INSERT statements to populate realistic data>",
  "answer_sql": "<correct SQL answer>",
  "expected_output_description": "<brief description of what the result set looks like>"
}}
"""


# ---------------------------------------------------------------------------
# Step functions (plain Python — no Prefect cloud)
# ---------------------------------------------------------------------------

def step1_load_taxonomy(schema_path: str) -> tuple[dict, list]:
    schema = load_schema(schema_path)
    topics = get_topic_pool()
    logger.info("Step1: taxonomy loaded. tables=%d topics=%d", len(schema.get("tables", {})), len(topics))
    return schema, topics


def step2_select_target(topics: list, difficulty: str, stats: dict) -> dict:
    get_difficulty_config(difficulty)

    existing_by_topic: dict = {k: v for k, v in stats.get("by_topic", {}).items()}
    sorted_topics = sorted(topics, key=lambda t: existing_by_topic.get(t["topic"], 0))
    chosen = sorted_topics[0] if sorted_topics else (topics[0] if topics else {"topic": "SELECT_BASIC"})
    chosen_topic = chosen["topic"] if isinstance(chosen, dict) else chosen

    logger.info("Step2: target selected. topic=%s difficulty=%s", chosen_topic, difficulty)
    return {"topic": chosen_topic, "difficulty": difficulty}


def step3_plan_question(difficulty: str, topic: str, schema: dict, llm: LLMGateway) -> QuestionBlueprint:
    blueprint = plan_question(difficulty=difficulty, topic=topic, schema=schema, llm=llm)
    logger.info("Step3: blueprint created. skill=%s", blueprint.target_skill)
    return blueprint


def step4_generate_question(
    blueprint: QuestionBlueprint,
    topic: str,
    schema: dict,
    llm: LLMGateway,
    attempt: int = 1,
    override_prompt: str | None = None,
) -> dict:
    schema_sql = generate_ddl(schema)
    seed_sql = generate_seed(schema)
    few_shot = get_few_shot_example(topic, blueprint.difficulty)

    base_prompt = _GENERATOR_PROMPT.format(
        schema_sql=schema_sql,
        difficulty=blueprint.difficulty,
        topic=topic,
        constructs=blueprint.target_skill,
        trap_strategy=blueprint.trap_strategy,
        few_shot=few_shot,
        seed_sql=seed_sql,
    )

    prompt = override_prompt if override_prompt else base_prompt
    raw = llm.generate("generator", prompt, expect_json=True)

    if raw.startswith("ERROR:"):
        raise ValueError(f"LLM generation failed: {raw}")

    # Strip markdown fences if present
    clean = raw.strip()
    if clean.startswith("```"):
        lines = clean.splitlines()
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
        clean = "\n".join(inner).strip()

    try:
        parsed = json.loads(clean)
    except json.JSONDecodeError as exc:
        raise ValueError(f"LLM did not return valid JSON: {exc}\nRaw: {raw[:300]}")

    missing = {"question_text", "schema_sql", "seed_sql", "answer_sql"} - parsed.keys()
    if missing:
        raise ValueError(f"LLM JSON missing keys: {missing}")

    parsed["expected_output"] = parsed.pop("expected_output_description", "")
    parsed["difficulty"] = blueprint.difficulty
    parsed["topic"] = topic
    parsed["generation_attempt"] = attempt
    parsed["blueprint"] = blueprint

    logger.info("Step4: question generated. topic=%s attempt=%d", topic, attempt)
    return parsed


def step5_clarity_check(question_text: str) -> dict:
    result = check_clarity(question_text)
    logger.info("Step5: clarity is_clear=%s score=%s", result.get("is_clear"), result.get("score"))
    return result


def step6_execution_verify(schema_sql: str, seed_sql: str, answer_sql: str) -> dict:
    result = verify_in_sandbox(schema_sql, seed_sql, answer_sql)
    logger.info("Step6: execution valid=%s rows=%s error=%s", result.get("valid"), result.get("row_count"), result.get("error"))
    return result


def step7_save_to_bank(question_data: dict, bank: QuestionBank) -> str:
    question_id = bank.save(question_data)
    logger.info("Step7: saved id=%s", question_id)
    return question_id


# ---------------------------------------------------------------------------
# Single question generation with retry
# ---------------------------------------------------------------------------

def _generate_one(
    difficulty: str,
    topic: str,
    schema: dict,
    llm: LLMGateway,
    bank: QuestionBank,
    max_retries: int = 3,
) -> dict:
    blueprint = step3_plan_question(difficulty=difficulty, topic=topic, schema=schema, llm=llm)
    last_prompt: str | None = None

    for attempt in range(1, max_retries + 2):
        if should_use_archive(attempt, max_retries):
            fallback = bank.get_archived_fallback(difficulty=difficulty, topic=topic)
            if fallback:
                logger.warning("Retries exhausted, using archive fallback id=%s", fallback["id"])
                return {"question_id": fallback["id"], "valid": bool(fallback["valid"]), "skipped": True}
            logger.error("Retries exhausted, no archive fallback. difficulty=%s topic=%s", difficulty, topic)
            return {"question_id": None, "valid": False, "skipped": True}

        override = get_retry_prompt(last_prompt or "", attempt, difficulty, topic) if attempt > 1 else None

        try:
            question_data = step4_generate_question(
                blueprint=blueprint, topic=topic, schema=schema,
                llm=llm, attempt=attempt, override_prompt=override,
            )
            last_prompt = override
        except Exception as exc:
            logger.warning("Step4 failed attempt=%d: %s", attempt, exc)
            last_prompt = None
            continue

        try:
            clarity = step5_clarity_check(question_data["question_text"])
            question_data["clarity_score"] = clarity.get("score", 0.0)
            if not clarity.get("is_clear", True):
                logger.warning("Clarity failed attempt=%d issues=%s", attempt, clarity.get("issues"))
                last_prompt = None
                continue
        except Exception as exc:
            logger.warning("Step5 failed attempt=%d: %s", attempt, exc)
            question_data["clarity_score"] = None

        try:
            verify_result = step6_execution_verify(
                question_data["schema_sql"], question_data["seed_sql"], question_data["answer_sql"],
            )
            question_data["valid"] = verify_result.get("valid", False)
            question_data["expected_output"] = verify_result.get("output", [])
            question_data.setdefault("metadata", {})["verify"] = {
                "row_count": verify_result.get("row_count"),
                "duration_ms": verify_result.get("duration_ms"),
                "error": verify_result.get("error"),
            }
            if not verify_result.get("valid", False):
                logger.warning("Execution failed attempt=%d error=%s", attempt, verify_result.get("error"))
                last_prompt = None
                continue
        except Exception as exc:
            logger.warning("Step6 failed attempt=%d: %s", attempt, exc)
            question_data["valid"] = False

        question_id = step7_save_to_bank(question_data, bank)
        return {"question_id": question_id, "valid": question_data.get("valid", False), "skipped": False}

    return {"question_id": None, "valid": False, "skipped": True}


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

def generate_pipeline(
    specs: list[str] = ["easy", "medium", "hard"],
    questions_per_spec: int = 1,
    schema_path: str = "schema.json",
) -> dict:
    llm = LLMGateway()
    bank = QuestionBank()

    schema, topics = step1_load_taxonomy(schema_path)
    stats = bank.get_stats()

    generated = 0
    valid_count = 0
    failed = 0
    question_ids: list[str] = []

    for difficulty in specs:
        for _ in range(questions_per_spec):
            target = step2_select_target(topics=topics, difficulty=difficulty, stats=stats)
            topic = target["topic"]

            result = _generate_one(difficulty=difficulty, topic=topic, schema=schema, llm=llm, bank=bank)

            if result["question_id"] is None:
                failed += 1
            else:
                if not result["skipped"]:
                    generated += 1
                question_ids.append(result["question_id"])
                if result["valid"]:
                    valid_count += 1

            stats = bank.get_stats()

    return {
        "generated": generated,
        "valid": valid_count,
        "failed": failed,
        "question_ids": [qid for qid in question_ids if qid],
        "stats": bank.get_stats(),
    }


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    result = generate_pipeline()
    print(json.dumps(result, indent=2, ensure_ascii=False))
