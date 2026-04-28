import httpx
import os
import logging
import time
from dotenv import load_dotenv

load_dotenv(override=True)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

JSON_INSTRUCTION = "\n\nRespond with ONLY valid JSON, no markdown, no explanation."


def _build_ollama_url() -> str:
    raw_url = os.getenv("OLLAMA_HOST", "http://localhost:11434")
    if "0.0.0.0" in raw_url:
        raw_url = raw_url.replace("0.0.0.0", "localhost")
    if ":11434" not in raw_url and "localhost" in raw_url:
        raw_url = raw_url.rstrip("/") + ":11434"
    return raw_url.rstrip("/")


class LLMGateway:
    def __init__(self):
        self.provider = os.getenv("AI_PROVIDER", "ollama").lower()

        if self.provider == "gemini":
            self.gemini_api_key = os.getenv("GEMINI_API_KEY", "")
            self.gemini_model = os.getenv("GEMINI_MODEL", "gemini-2.0-flash")
            self._init_gemini()
        else:
            self.base_url = _build_ollama_url()
            self.model = os.getenv("MODEL_NAME", "llama3")
            self.api_key = os.getenv("OLLAMA_API_KEY", "")

        logger.info(
            "LLMGateway initialized. provider=%s model=%s",
            self.provider,
            self.gemini_model if self.provider == "gemini" else self.model,
        )

    def _init_gemini(self):
        try:
            import google.generativeai as genai

            genai.configure(api_key=self.gemini_api_key)
            self._genai = genai
            self._gemini_client = genai.GenerativeModel(self.gemini_model)
            logger.info("Gemini client ready. model=%s", self.gemini_model)
        except ImportError:
            raise RuntimeError(
                "google-generativeai package not installed. Run: pip install google-generativeai"
            )

    def _generate_gemini(self, prompt: str) -> str:
        for attempt in range(3):
            try:
                response = self._gemini_client.generate_content(prompt)
                return response.text.strip()
            except Exception as e:
                logger.error("Gemini attempt %d failed: %s", attempt + 1, e)
                if attempt < 2:
                    time.sleep(2 ** attempt)
        return "ERROR: Gemini LLM failed after retries"

    def _generate_ollama(self, prompt: str) -> str:
        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "options": {"num_ctx": 8192},
        }

        headers = {}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        for attempt in range(3):
            try:
                res = httpx.post(
                    f"{self.base_url}/api/generate",
                    json=payload,
                    headers=headers,
                    timeout=180.0,
                )
                if res.status_code != 200:
                    logger.error("Ollama non-200 response: %s", res.text)
                    time.sleep(2)
                    continue
                return res.json().get("response", "").strip()
            except Exception as e:
                logger.error("Ollama attempt %d failed: %s", attempt + 1, e)
                time.sleep(2)

        return "ERROR: Ollama LLM failed after retries"

    def generate(self, task_type: str, prompt: str, expect_json: bool = False) -> str:
        """
        task_type: "planner" | "generator" | "clarity"
        expect_json: if True, appends JSON-only instruction to prompt
        """
        if expect_json:
            prompt = prompt + JSON_INSTRUCTION

        logger.info(
            "LLM call. provider=%s task=%s expect_json=%s",
            self.provider,
            task_type,
            expect_json,
        )

        if self.provider == "gemini":
            return self._generate_gemini(prompt)
        else:
            return self._generate_ollama(prompt)