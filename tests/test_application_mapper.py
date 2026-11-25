import unittest

from app.codebase.application_mapper import ApplicationMapper


class TestApplicationMapper(unittest.TestCase):

    def setUp(self):
        self.mapper = ApplicationMapper()

    def map_form(
        self,
        form,
        routes=None,
        rendered_templates=None,
        scripts=None,
        handlers=None,
    ):
        python_analysis = {
            "flask_routes": routes or [],
            "rendered_templates": rendered_templates or [],
        }

        template_analysis = {
            "files": [
                {
                    "file_path": "templates/review.html",
                    "forms": [form],
                    "script_references": scripts or [],
                }
            ]
        }

        javascript_analysis = {
            "form_handlers": handlers or [],
        }

        return self.mapper.map_application(
            python_analysis,
            template_analysis,
            javascript_analysis,
        )

    def test_maps_explicit_action_to_matching_backend_route(self):
        result = self.map_form(
            {
                "id": "review-form",
                "action": "{{ url_for('submit_review') }}",
                "method": "POST",
                "fields": [],
            },
            routes=[
                {
                    "function": "submit_review",
                    "path": "/reviews",
                    "methods": ["POST"],
                }
            ],
        )

        mapping = result["form_mappings"][0]

        self.assertEqual(mapping["mapping_status"], "matched")
        self.assertEqual(mapping["backend_function"], "submit_review")
        self.assertEqual(mapping["backend_path"], "/reviews")

    def test_explicit_action_without_matching_route_is_unmapped(self):
        result = self.map_form(
            {
                "id": "review-form",
                "action": "{{ url_for('submit_review') }}",
                "method": "POST",
                "fields": [],
            },
            routes=[
                {
                    "function": "reviews",
                    "path": "/reviews",
                    "methods": ["GET"],
                }
            ],
        )

        mapping = result["form_mappings"][0]

        self.assertEqual(mapping["mapping_status"], "unmapped")
        self.assertIsNone(mapping.get("backend_function"))

    def test_template_rendering_route_does_not_prove_form_submission(self):
        result = self.map_form(
            {
                "id": "review-form",
                "action": "",
                "method": "GET",
                "fields": [],
            },
            routes=[
                {
                    "function": "reviews",
                    "path": "/reviews",
                    "methods": ["GET"],
                }
            ],
            rendered_templates=[
                {
                    "function": "reviews",
                    "template": "review.html",
                }
            ],
        )

        mapping = result["form_mappings"][0]

        self.assertEqual(mapping["mapping_status"], "unverified")
        self.assertIsNone(mapping.get("backend_function"))

    def test_referenced_client_side_handler_is_classified(self):
        result = self.map_form(
            {
                "id": "review-form",
                "action": "",
                "method": "GET",
                "fields": [],
            },
            scripts=["/static/scripts.js"],
            handlers=[
                {
                    "form_id": "review-form",
                    "file_path": "static/scripts.js",
                    "prevents_default": True,
                    "network_requests": [],
                    "handling_type": "client_side",
                }
            ],
        )

        mapping = result["form_mappings"][0]

        self.assertEqual(mapping["mapping_status"], "client_side")
        self.assertEqual(mapping["handling_type"], "client_side")

    def test_referenced_network_handler_is_classified(self):
        result = self.map_form(
            {
                "id": "contact-form",
                "action": "",
                "method": "GET",
                "fields": [],
            },
            scripts=["/static/contact.js"],
            handlers=[
                {
                    "form_id": "contact-form",
                    "file_path": "static/contact.js",
                    "prevents_default": True,
                    "network_requests": ["fetch"],
                    "handling_type": "javascript_submission",
                }
            ],
        )

        mapping = result["form_mappings"][0]

        self.assertEqual(
            mapping["mapping_status"],
            "javascript_submission",
        )
        self.assertEqual(
            mapping["handling_type"],
            "javascript_submission",
        )

    def test_resolves_flask_static_url_for_script_reference(self):
        result = self.map_form(
            {
                "id": "review-form",
                "action": "",
                "method": "GET",
                "fields": [],
            },
            scripts=[
                "{{ url_for('static', filename='scripts.js') }}"
            ],
            handlers=[
                {
                    "form_id": "review-form",
                    "file_path": "static/scripts.js",
                    "prevents_default": True,
                    "network_requests": [],
                    "handling_type": "client_side",
                }
            ],
        )

        mapping = result["form_mappings"][0]

        self.assertEqual(mapping["mapping_status"], "client_side")
        self.assertEqual(mapping["handling_type"], "client_side")

    def test_unreferenced_javascript_is_not_associated_with_form(self):
        result = self.map_form(
            {
                "id": "review-form",
                "action": "",
                "method": "GET",
                "fields": [],
            },
            scripts=["/static/reviews.js"],
            handlers=[
                {
                    "form_id": "review-form",
                    "file_path": "static/unrelated.js",
                    "prevents_default": True,
                    "network_requests": [],
                    "handling_type": "client_side",
                }
            ],
        )

        mapping = result["form_mappings"][0]

        self.assertEqual(mapping["mapping_status"], "unverified")

    def test_counts_each_form_once(self):
        python_analysis = {
            "flask_routes": [
                {
                    "function": "submit_review",
                    "path": "/reviews",
                    "methods": ["POST"],
                },
                {
                    "function": "submit_review",
                    "path": "/submit-review",
                    "methods": ["POST"],
                },
            ],
            "rendered_templates": [],
        }

        template_analysis = {
            "files": [
                {
                    "file_path": "templates/review.html",
                    "forms": [
                        {
                            "id": "review-form",
                            "action": "{{ url_for('submit_review') }}",
                            "method": "POST",
                            "fields": [],
                        }
                    ],
                    "script_references": [],
                }
            ]
        }

        result = self.mapper.map_application(
            python_analysis,
            template_analysis,
        )

        self.assertEqual(result["total_forms"], 1)
        self.assertEqual(len(result["form_mappings"]), 1)


if __name__ == "__main__":
    unittest.main()
