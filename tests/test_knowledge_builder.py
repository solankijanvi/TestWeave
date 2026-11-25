import unittest

from app.knowledge.knowledge_builder import KnowledgeBuilder


class TestApplicationMetadata(unittest.TestCase):

    def setUp(self):
        self.builder = KnowledgeBuilder()

    def build_knowledge(self, repository, files=None):
        return self.builder.build(
            repository_data={
                "repository": repository,
                "files": files or [],
            },
            python_result={},
            template_result={},
            mapping_result={},
            data_flow_result={},
        )

    def test_uses_github_description_when_available(self):
        knowledge = self.build_knowledge(
            repository={
                "full_name": "owner/project",
                "description": "GitHub repository description",
                "default_branch": "main",
            },
            files=[
                {
                    "path": "README.md",
                    "content": (
                        "# Project\n\n"
                        "README description."
                    ),
                }
            ],
        )

        self.assertEqual(
            knowledge["application"]["description"],
            "GitHub repository description",
        )

    def test_uses_readme_description_as_fallback(self):
        knowledge = self.build_knowledge(
            repository={
                "full_name": "owner/project",
                "description": None,
                "default_branch": "main",
            },
            files=[
                {
                    "path": "README.md",
                    "content": (
                        "# BovineGuard\n\n"
                        "BovineGuard is a web application "
                        "for cattle disease prediction.\n\n"
                        "## Features\n\n"
                        "Some additional details."
                    ),
                }
            ],
        )

        self.assertEqual(
            knowledge["application"]["description"],
            (
                "BovineGuard is a web application "
                "for cattle disease prediction."
            ),
        )

    def test_returns_none_when_description_sources_are_missing(self):
        knowledge = self.build_knowledge(
            repository={
                "full_name": "owner/project",
                "description": None,
                "default_branch": "main",
            }
        )

        self.assertIsNone(
            knowledge["application"]["description"]
        )

    def test_preserves_detailed_form_mapping_statuses(self):
        mapping_result = {
            "mapped_forms": [
                {
                    "template": "templates/contact.html",
                    "form_id": "contact-form",
                    "mapping_status": "matched",
                }
            ],
            "unmapped_forms": [
                {
                    "template": "templates/review.html",
                    "form_id": "review-form",
                    "mapping_status": "client_side",
                    "reason": "Client-side submission detected.",
                },
                {
                    "template": "templates/about.html",
                    "form_id": "about-form",
                    "mapping_status": "unverified",
                    "reason": "Submission behavior is unverified.",
                },
                {
                    "template": "templates/feedback.html",
                    "form_id": "feedback-form",
                    "mapping_status": "unmapped",
                    "reason": "No matching backend route.",
                },
            ],
        }

        knowledge = self.builder.build(
            repository_data={
                "repository": {},
                "files": [],
            },
            python_result={},
            template_result={},
            mapping_result=mapping_result,
            data_flow_result={},
        )

        mappings = {
            mapping["form_id"]: mapping
            for mapping in knowledge["form_route_mappings"]
        }

        self.assertEqual(
            mappings["contact-form"]["mapping_status"],
            "matched",
        )
        self.assertEqual(
            mappings["review-form"]["mapping_status"],
            "client_side",
        )
        self.assertEqual(
            mappings["about-form"]["mapping_status"],
            "unverified",
        )
        self.assertEqual(
            mappings["feedback-form"]["mapping_status"],
            "unmapped",
        )

    def test_counts_form_mapping_statuses(self):
        mapping_result = {
            "mapped_forms": [
                {"mapping_status": "matched"},
                {"mapping_status": "matched"},
            ],
            "unmapped_forms": [
                {"mapping_status": "client_side"},
                {"mapping_status": "javascript_submission"},
                {"mapping_status": "unmapped"},
                {"mapping_status": "unverified"},
            ],
        }

        knowledge = self.builder.build(
            repository_data={
                "repository": {},
                "files": [],
            },
            python_result={},
            template_result={},
            mapping_result=mapping_result,
            data_flow_result={},
        )

        self.assertEqual(
            knowledge["statistics"]["form_mapping_status_counts"],
            {
                "matched": 2,
                "client_side": 1,
                "javascript_submission": 1,
                "unmapped": 1,
                "unverified": 1,
            },
        )
if __name__ == "__main__":
    unittest.main()
