import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch

from pydantic import ValidationError

from app.ai.llm_client import LLMClient
from app.ai.schemas import AIPageAnalysis


class TestLLMClient(unittest.TestCase):

    def setUp(self):
        self.load_dotenv_patcher = patch("app.ai.llm_client.load_dotenv")
        self.getenv_patcher = patch(
            "app.ai.llm_client.os.getenv",
            return_value="fake-api-key"
        )
        self.client_patcher = patch("app.ai.llm_client.genai.Client")

        self.load_dotenv_patcher.start()
        self.getenv_patcher.start()
        self.mock_client_factory = self.client_patcher.start()

        self.addCleanup(self.load_dotenv_patcher.stop)
        self.addCleanup(self.getenv_patcher.stop)
        self.addCleanup(self.client_patcher.stop)

        self.mock_client = Mock()
        self.mock_client_factory.return_value = self.mock_client

        self.llm = LLMClient()

    def test_initializes_with_api_key(self):
        self.mock_client_factory.assert_called_once_with(
            api_key="fake-api-key"
        )

        self.assertEqual(self.llm.model, "gemini-flash-latest")

    def test_raises_error_when_api_key_is_missing(self):
        with patch("app.ai.llm_client.os.getenv", return_value=None):
            with self.assertRaisesRegex(
                ValueError,
                "GEMINI_API_KEY is not set."
            ):
                LLMClient()

    def test_generate_returns_response_text(self):
        self.mock_client.models.generate_content.return_value = (
            SimpleNamespace(text="An API enables communication between systems.")
        )

        result = self.llm.generate("Explain what an API is.")

        self.assertEqual(
            result,
            "An API enables communication between systems."
        )

        self.mock_client.models.generate_content.assert_called_once_with(
            model="gemini-flash-latest",
            contents="Explain what an API is."
        )

    def test_generate_rejects_empty_response(self):
        for response_text in ("", None):
            with self.subTest(response_text=response_text):
                self.mock_client.models.generate_content.return_value = (
                    SimpleNamespace(text=response_text)
                )

                with self.assertRaisesRegex(
                    ValueError,
                    "Gemini returned an empty response."
                ):
                    self.llm.generate("Explain what an API is.")

    def test_generate_structured_returns_valid_schema(self):
        response_json = """
        {
            "page_purpose": "Prediction",
            "functionality": "Predicts cattle diseases.",
            "user_actions": ["Enter age", "Select symptoms"],
            "evidence": ["Prediction form detected"],
            "confidence": "high"
        }
        """

        self.mock_client.models.generate_content.return_value = (
            SimpleNamespace(text=response_json)
        )

        result = self.llm.generate_structured(
            "Analyze this page.",
            AIPageAnalysis
        )

        self.assertIsInstance(result, AIPageAnalysis)
        self.assertEqual(result.page_purpose, "Prediction")
        self.assertEqual(result.confidence, "high")

        self.mock_client.models.generate_content.assert_called_once_with(
            model="gemini-flash-latest",
            contents="Analyze this page.",
            config={
                "response_mime_type": "application/json",
                "response_schema": AIPageAnalysis,
            }
        )

    def test_generate_structured_rejects_empty_response(self):
        self.mock_client.models.generate_content.return_value = (
            SimpleNamespace(text="")
        )

        with self.assertRaisesRegex(
            ValueError,
            "Gemini returned an empty response."
        ):
            self.llm.generate_structured(
                "Analyze this page.",
                AIPageAnalysis
            )

    def test_generate_structured_rejects_invalid_schema_data(self):
        invalid_json = """
        {
            "page_purpose": "Prediction",
            "functionality": "Predicts cattle diseases.",
            "user_actions": [],
            "evidence": [],
            "confidence": "very_high"
        }
        """

        self.mock_client.models.generate_content.return_value = (
            SimpleNamespace(text=invalid_json)
        )

        with self.assertRaises(ValidationError):
            self.llm.generate_structured(
                "Analyze this page.",
                AIPageAnalysis
            )


if __name__ == "__main__":
    unittest.main()
