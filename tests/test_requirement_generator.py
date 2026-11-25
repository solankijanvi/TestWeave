
import unittest
from unittest.mock import Mock

from app.ai.requirement_generator import (
    analyze_page,
    build_observations,
    fallback_analysis,
)
from app.ai.schemas import AIPageAnalysis


class TestBuildObservations(unittest.TestCase):

    def test_extracts_observed_page_details(self):
        page = {
            "url": "https://example.com/predict",
            "title": "Prediction",
            "headings": ["Cattle Prediction"],
            "text": "Enter cattle details.",
            "links": [{"text": "Home", "href": "/"}],
            "buttons": [{"text": "Predict"}],
            "inputs": [{"name": "age", "type": "number"}],
            "selects": [
                {
                    "name": "symptoms",
                    "options": ["Fever", "Cough"],
                }
            ],
            "textareas": [{"name": "description"}],
            "forms": [{"id": "prediction-form"}],
        }

        result = build_observations(page)

        self.assertEqual(result["url"], page["url"])
        self.assertEqual(result["title"], "Prediction")
        self.assertEqual(result["headings"], ["Cattle Prediction"])
        self.assertEqual(result["inputs"], page["inputs"])
        self.assertEqual(result["forms"], page["forms"])
        self.assertEqual(
            result["selects"],
            [{"name": "symptoms", "id": None, "options_count": 2}],
        )

    def test_limits_visible_text_and_links(self):
        page = {
            "text": "x" * 3000,
            "links": [{"href": f"/page/{i}"} for i in range(40)],
        }

        result = build_observations(page)

        self.assertEqual(len(result["visible_text"]), 2500)
        self.assertEqual(len(result["links"]), 30)

    def test_handles_missing_optional_page_fields(self):
        result = build_observations({})

        self.assertEqual(result["url"], "")
        self.assertEqual(result["title"], "")
        self.assertEqual(result["headings"], [])
        self.assertEqual(result["visible_text"], "")
        self.assertEqual(result["links"], [])
        self.assertEqual(result["forms"], [])


class TestFallbackAnalysis(unittest.TestCase):

    def test_predict_page_gets_prediction_purpose(self):
        observations = {
            "url": "https://example.com/predict",
            "title": "Cattle Disease Prediction",
            "headings": ["Predict Disease"],
            "inputs": [{"name": "age", "type": "number"}],
            "selects": [{"name": "symptoms"}],
            "textareas": [{"name": "notes"}],
            "buttons": [{"text": "Submit"}],
            "forms": [{}],
        }

        result = fallback_analysis(observations)

        self.assertIsInstance(result, AIPageAnalysis)
        self.assertEqual(result.page_purpose, "Prediction")
        self.assertEqual(result.confidence, "low")
        self.assertIn("Enter age", result.user_actions)
        self.assertIn("Select an option for symptoms", result.user_actions)
        self.assertIn("Enter text in notes", result.user_actions)
        self.assertIn("Click Submit", result.user_actions)
        self.assertTrue(result.evidence)

    def test_unknown_page_gets_unknown_purpose(self):
        observations = {
            "url": "https://example.com/dashboard",
            "title": "Dashboard",
            "headings": [],
            "inputs": [],
            "selects": [],
            "textareas": [],
            "buttons": [],
            "forms": [],
        }

        result = fallback_analysis(observations)

        self.assertEqual(result.page_purpose, "Unknown")
        self.assertEqual(result.confidence, "low")


class TestAnalyzePage(unittest.TestCase):

    def setUp(self):
        self.page = {
            "url": "https://example.com/predict",
            "title": "Prediction",
            "headings": ["Predict Disease"],
            "text": "Enter cattle details.",
            "links": [],
            "buttons": [],
            "inputs": [],
            "selects": [],
            "textareas": [],
            "forms": [],
        }

        self.expected_analysis = AIPageAnalysis(
            page_purpose="Prediction",
            functionality="Predicts cattle diseases.",
            user_actions=["Enter cattle details"],
            evidence=["Prediction form detected"],
            confidence="high",
        )

    def test_returns_gemini_analysis_when_llm_succeeds(self):
        llm = Mock()
        structured_llm = Mock()
        structured_llm.invoke.return_value = self.expected_analysis
        llm.with_structured_output.return_value = structured_llm

        result, source = analyze_page(llm, self.page)

        self.assertEqual(result, self.expected_analysis)
        self.assertEqual(source, "gemini_langchain")
        llm.with_structured_output.assert_called_once_with(AIPageAnalysis)
        structured_llm.invoke.assert_called_once()

    def test_returns_fallback_when_llm_fails(self):
        llm = Mock()
        llm.with_structured_output.side_effect = RuntimeError(
            "Simulated Gemini failure"
        )

        result, source = analyze_page(llm, self.page)

        self.assertIsInstance(result, AIPageAnalysis)
        self.assertEqual(source, "fallback")
        self.assertEqual(result.page_purpose, "Prediction")
        self.assertEqual(result.confidence, "low")


if __name__ == "__main__":
    unittest.main()