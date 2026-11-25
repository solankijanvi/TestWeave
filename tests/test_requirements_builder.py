import unittest
from unittest.mock import Mock
from pydantic import ValidationError

from app.ai.requirements_builder import (
    Requirement,
    RequirementsDocument,
    build_fallback_requirements,
    generate_page_requirements,
    build_requirement_prompt,
)

class TestBuildFallbackRequirements(unittest.TestCase):

    def test_generates_requirements_from_observed_elements(self):
        page = {
            "url": "https://example.com/predict",
            "links": [
                {"text": "Home", "href": "/"}
            ],
            "inputs": [
                {"name": "age", "type": "number"}
            ],
            "selects": [
                {"name": "symptoms"}
            ],
            "textareas": [
                {"name": "description"}
            ],
            "buttons": [
                {"text": "Predict"}
            ],
            "forms": [
                {"id": "prediction-form"}
            ],
        }

        result = build_fallback_requirements(page, start_id=1)

        self.assertEqual(len(result), 6)
        self.assertTrue(
            all(isinstance(item, Requirement) for item in result)
        )

        self.assertEqual(
            [item.requirement_id for item in result],
            [f"REQ-{i:03d}" for i in range(1, 7)],
        )

        self.assertTrue(
            all(item.source_url == page["url"] for item in result)
        )

        self.assertIn(
            "Navigation link: Home",
            [item.title for item in result],
        )
        self.assertIn(
            "Input field: age",
            [item.title for item in result],
        )
        self.assertIn(
            "Dropdown: symptoms",
            [item.title for item in result],
        )
        self.assertIn(
            "Text area: description",
            [item.title for item in result],
        )
        self.assertIn(
            "Button: Predict",
            [item.title for item in result],
        )

    def test_excludes_hidden_inputs(self):
        page = {
            "url": "https://example.com/login",
            "inputs": [
                {"name": "username", "type": "text"},
                {"name": "csrf_token", "type": "hidden"},
            ],
        }

        result = build_fallback_requirements(page, start_id=1)

        titles = [item.title for item in result]

        self.assertIn("Input field: username", titles)
        self.assertNotIn("Input field: csrf_token", titles)

    def test_creates_inferred_requirement_for_informational_page(self):
        page = {
            "url": "https://example.com/about",
            "title": "About Us",
            "headings": ["Our Mission", "Our Vision"],
        }

        result = build_fallback_requirements(page, start_id=5)

        self.assertEqual(len(result), 1)

        requirement = result[0]

        self.assertEqual(requirement.requirement_id, "REQ-005")
        self.assertEqual(requirement.title, "Informational page: About Us")
        self.assertEqual(requirement.requirement_type, "inferred")
        self.assertEqual(requirement.confidence, "low")
        self.assertEqual(
            requirement.source_url,
            "https://example.com/about",
        )
        self.assertTrue(requirement.evidence)

    def test_returns_empty_list_when_page_has_no_evidence(self):
        page = {
            "url": "https://example.com/empty",
        }

        result = build_fallback_requirements(page, start_id=1)

        self.assertEqual(result, [])

    def test_preserves_requirement_evidence_and_source_url(self):
        page = {
            "url": "https://example.com/contact",
            "buttons": [
                {"text": "Send Message"}
            ],
        }

        result = build_fallback_requirements(page, start_id=10)

        self.assertEqual(len(result), 1)

        requirement = result[0]

        self.assertEqual(requirement.requirement_id, "REQ-010")
        self.assertEqual(
            requirement.source_url,
            "https://example.com/contact",
        )
        self.assertEqual(requirement.requirement_type, "observed")
        self.assertTrue(requirement.evidence)
        self.assertIn("Send Message", requirement.evidence[0])


class TestRequirementSchema(unittest.TestCase):

    def test_accepts_valid_requirement(self):
        requirement = Requirement(
            requirement_id="REQ-001",
            title="Input field: age",
            description="The page contains an age input field.",
            source_url="https://example.com/predict",
            evidence=["Observed input name: age"],
            requirement_type="observed",
            confidence="high",
        )

        self.assertEqual(requirement.requirement_id, "REQ-001")
        self.assertEqual(requirement.requirement_type, "observed")

    def test_rejects_invalid_requirement_type(self):
        from pydantic import ValidationError

        with self.assertRaises(ValidationError):
            Requirement(
                requirement_id="REQ-001",
                title="Invalid requirement",
                description="Invalid type.",
                source_url="https://example.com",
                evidence=["Test evidence"],
                requirement_type="unknown",
                confidence="low",
            )

    def test_rejects_invalid_confidence(self):
        from pydantic import ValidationError

        with self.assertRaises(ValidationError):
            Requirement(
                requirement_id="REQ-001",
                title="Invalid confidence",
                description="Invalid confidence value.",
                source_url="https://example.com",
                evidence=["Test evidence"],
                requirement_type="observed",
                confidence="very_high",
            )

    def test_rejects_empty_source_url(self):
        with self.assertRaises(ValueError):
            Requirement(
                requirement_id="REQ-001",
                title="Prediction form",
                description="The page contains a prediction form.",
                source_url="",
                evidence=["Observed form"],
                requirement_type="observed",
                confidence="high",
            )

    def test_rejects_empty_evidence(self):
        with self.assertRaises(ValueError):
            Requirement(
                requirement_id="REQ-001",
                title="Prediction form",
                description="The page contains a prediction form.",
                source_url="https://example.com/predict",
                evidence=[],
                requirement_type="observed",
                confidence="high",
            )

    def test_rejects_missing_evidence(self):
        with self.assertRaises(ValidationError):
            Requirement(
                requirement_id="REQ-001",
                title="Prediction form",
                description="The page contains a prediction form.",
                source_url="https://example.com/predict",
                requirement_type="observed",
                confidence="high",
            )

class TestGeneratePageRequirements(unittest.TestCase):

    def setUp(self):
        self.page = {
            "url": "https://example.com/predict",
            "title": "Prediction",
            "buttons": [{"text": "Submit"}],
        }

        self.page_analysis = {
            "analysis": {
                "page_purpose": "Allows users to submit prediction details.",
                "functionality": "Contains a prediction form.",
                "user_actions": ["Click Submit"],
                "evidence": ["Submit button detected"],
                "confidence": "medium",
            },
            "analysis_source": "gemini",
        }

        self.requirement = Requirement(
            requirement_id="TEMP-001",
            title="Submit prediction",
            description="The page contains a Submit button.",
            source_url=self.page["url"],
            evidence=["Observed button: Submit"],
            requirement_type="observed",
            confidence="high",
        )

    def test_returns_gemini_requirements_when_llm_succeeds(self):
        llm = Mock()

        llm.with_structured_output.return_value.invoke.return_value = (
            RequirementsDocument(requirements=[self.requirement])
        )

        requirements, source = generate_page_requirements(
            self.page,
            self.page_analysis,
            llm,
        )

        self.assertEqual(source, "gemini")
        self.assertEqual(len(requirements), 1)
        self.assertEqual(requirements[0].title, "Submit prediction")

    def test_returns_fallback_when_gemini_output_is_invalid(self):
        invalid_requirement = {
            "requirement_id": "TEMP-001",
            "title": "Submit prediction",
            "description": "The page contains a Submit button.",
            "source_url": self.page["url"],
            "evidence": [],
            "requirement_type": "observed",
            "confidence": "high",
        }

        llm = Mock()
        llm.with_structured_output.return_value.invoke.return_value = {
            "requirements": [invalid_requirement]
        }

        requirements, source = generate_page_requirements(
            self.page,
            self.page_analysis,
            llm,
        )

        self.assertEqual(source, "fallback")
        self.assertTrue(requirements)
        self.assertTrue(
            all(requirement.evidence for requirement in requirements)
        )
        self.assertEqual(
            requirements[0].source_url,
            self.page["url"],
        )

    def test_returns_fallback_when_llm_fails(self):
        llm = Mock()
        llm.with_structured_output.return_value.invoke.side_effect = (
            RuntimeError("Simulated LLM failure")
        )

        requirements, source = generate_page_requirements(
            self.page,
            self.page_analysis,
            llm,
        )

        self.assertEqual(source, "fallback")
        self.assertTrue(requirements)
        self.assertEqual(
            requirements[0].source_url,
            self.page["url"],
        )

    def test_uses_fallback_when_llm_is_none(self):
        requirements, source = generate_page_requirements(
            self.page,
            self.page_analysis,
            llm=None,
        )

        self.assertEqual(source, "fallback")
        self.assertTrue(requirements)
        self.assertEqual(
            requirements[0].source_url,
            self.page["url"],
        )

class TestBuildRequirementPrompt(unittest.TestCase):

    def test_includes_page_observations_and_analysis(self):
        page = {
            "url": "https://example.com/predict",
            "title": "Prediction",
            "headings": ["Cattle Prediction"],
            "text": "Enter cattle details",
            "links": [{"text": "Home", "href": "/"}],
        }

        page_analysis = {
            "analysis": {
                "page_purpose": "Predict cattle disease",
                "functionality": "Allows users to submit cattle details.",
            },
            "analysis_source": "gemini",
        }

        prompt = build_requirement_prompt(page, page_analysis)

        self.assertIn("https://example.com/predict", prompt)
        self.assertIn("Cattle Prediction", prompt)
        self.assertIn("Predict cattle disease", prompt)
        self.assertIn("gemini", prompt)

    def test_limits_page_text_to_1500_characters(self):
        page = {
            "url": "https://example.com",
            "text": "A" * 1600,
        }

        prompt = build_requirement_prompt(page, {})

        self.assertIn("A" * 1500, prompt)
        self.assertNotIn("A" * 1501, prompt)

    def test_limits_links_to_30(self):
        page = {
            "url": "https://example.com",
            "links": [
                {"text": f"Link {i}", "href": f"/page-{i}"}
                for i in range(35)
            ],
        }

        prompt = build_requirement_prompt(page, {})

        self.assertIn("Link 29", prompt)
        self.assertNotIn("Link 30", prompt)
        self.assertNotIn("Link 34", prompt)

if __name__ == "__main__":
    unittest.main()
