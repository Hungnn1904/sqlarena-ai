import httpx, os, logging, time
from dotenv import load_dotenv

load_dotenv(override=True)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class LLMGateway:
    def __init__(self):
        raw_url = os.getenv("OLLAMA_HOST", "http://localhost:11434")
        self.model = os.getenv("MODEL_NAME", "llama3")

        if "0.0.0.0" in raw_url:
            raw_url = raw_url.replace("0.0.0.0", "localhost")

        if ":11434" not in raw_url:
            raw_url = raw_url.rstrip('/') + ":11434"

        self.base_url = raw_url
        logger.info(f"LLM Gateway initialized. URL: {self.base_url}, Model: {self.model}")

    def generate(self, task_type, prompt):
        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "num_ctx": 2048   # 🔥 FIX QUAN TRỌNG: giảm RAM usage
            }
        }

        for attempt in range(3):  # 🔥 retry chống crash
            try:
                res = httpx.post(
                    f"{self.base_url}/api/generate",
                    json=payload,
                    timeout=180.0
                )

                if res.status_code != 200:
                    logger.error(f"Ollama Error Response: {res.text}")
                    time.sleep(2)
                    continue

                return res.json().get("response", "").strip()

            except Exception as e:
                logger.error(f"Retry {attempt+1} failed: {str(e)}")
                time.sleep(2)

        return "ERROR: LLM failed after retries"