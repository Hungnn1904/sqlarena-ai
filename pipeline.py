from prefect import flow, task
from llm_gateway import LLMGateway
import json, re, os, sqlglot, time
from dotenv import load_dotenv
from datetime import datetime

load_dotenv()

llm = LLMGateway()

SCHEMA = {
  "tables": {
    "employees": {"columns": {"id": "INTEGER", "name": "VARCHAR", "department_id": "INTEGER", "role": "VARCHAR"}},
    "departments": {"columns": {"id": "INTEGER", "name": "VARCHAR"}},
    "products": {"columns": {"product_id": "INTEGER", "category_id": "INTEGER", "price": "DECIMAL", "stock": "INTEGER"}},
    "sales": {"columns": {"sale_id": "INTEGER", "product_id": "INTEGER", "quantity": "INTEGER"}}
  }
}

def extract_sql(raw):
    match = re.search(r'(\{[\s\S]*"sql"[\s\S]*\})', raw)
    if match:
        try:
            return json.loads(match.group(1)).get("sql")
        except:
            return None
    return None


@task
def generator(spec):
    prompt = f"""
You are a SQL expert.

Schema:
{json.dumps(SCHEMA)}

Generate SQL question for: {spec}

Return ONLY JSON:
{{"question": "...", "sql": "...", "difficulty": "{spec}"}}
"""
    return llm.generate("generator", prompt)


@task
def validate(raw):
    sql = extract_sql(raw)
    if not sql:
        return {"valid": False, "error": "No SQL found"}

    try:
        sqlglot.parse_one(sql)
        return {"valid": True}
    except Exception as e:
        return {"valid": False, "error": str(e)}


@flow(name="SQL Question Generator Pipeline")
def generate_pipeline(specs=["easy", "medium", "hard"]):

    results = []

    for spec in specs:
        raw_output = generator(spec)

        time.sleep(2)  # 🔥 chống Llama crash

        val = validate(raw_output)

        parsed_raw = raw_output
        try:
            parsed_raw = json.loads(raw_output)
        except:
            pass

        results.append({
            "spec": spec,
            "valid": val["valid"],
            "raw": parsed_raw
        })

    date_str = datetime.now().strftime('%Y-%m-%d')
    output_dir = os.path.join("Output", date_str)
    os.makedirs(output_dir, exist_ok=True)

    filename = f"sql_questions_{'_'.join(specs)}_{datetime.now().strftime('%H%M%S')}.json"
    filepath = os.path.join(output_dir, filename)

    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=4, ensure_ascii=False)

    print(f"[INFO] Saved: {filepath}")

    return results


if __name__ == "__main__":
    generate_pipeline()