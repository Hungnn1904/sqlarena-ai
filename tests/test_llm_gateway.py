import os
import unittest
from unittest.mock import Mock, patch

from llm_gateway import LLMGateway


class OllamaJsonModeTests(unittest.TestCase):
    @patch("llm_gateway.httpx.post")
    def test_requests_json_format_when_expected(self, mock_post):
        response = Mock(status_code=200)
        response.json.return_value = {"response": '{"ok": true}'}
        mock_post.return_value = response
        with patch.dict(os.environ, {"AI_PROVIDER": "ollama"}, clear=False):
            gateway = LLMGateway()
            result = gateway.generate("generator", "Return JSON", expect_json=True)

        payload = mock_post.call_args.kwargs["json"]
        self.assertEqual(payload["format"], "json")
        self.assertEqual(result, '{"ok": true}')

    @patch("llm_gateway.httpx.post")
    def test_does_not_force_json_for_plain_text(self, mock_post):
        response = Mock(status_code=200)
        response.json.return_value = {"response": "plain text"}
        mock_post.return_value = response
        with patch.dict(os.environ, {"AI_PROVIDER": "ollama"}, clear=False):
            gateway = LLMGateway()
            gateway.generate("other", "Return text")

        payload = mock_post.call_args.kwargs["json"]
        self.assertNotIn("format", payload)


class NvidiaGatewayTests(unittest.TestCase):
    @patch("llm_gateway.httpx.post")
    def test_calls_nvidia_chat_completions(self, mock_post):
        response = Mock()
        response.raise_for_status.return_value = None
        response.json.return_value = {
            "choices": [{"message": {"content": '{"ok": true}'}}]
        }
        mock_post.return_value = response

        with patch.dict(
            os.environ,
            {
                "AI_PROVIDER": "nvidia",
                "NVIDIA_API_KEY": "test-key",
                "NVIDIA_MODEL": "google/gemma-4-31b-it",
            },
            clear=False,
        ):
            gateway = LLMGateway()
            result = gateway.generate("generator", "Return JSON", expect_json=True)

        request = mock_post.call_args.kwargs
        self.assertEqual(request["json"]["model"], "google/gemma-4-31b-it")
        self.assertEqual(request["headers"]["Authorization"], "Bearer test-key")
        self.assertEqual(result, '{"ok": true}')

    def test_requires_api_key(self):
        with patch.dict(
            os.environ,
            {"AI_PROVIDER": "nvidia", "NVIDIA_API_KEY": ""},
            clear=False,
        ):
            with self.assertRaisesRegex(RuntimeError, "NVIDIA_API_KEY"):
                LLMGateway()


if __name__ == "__main__":
    unittest.main()
