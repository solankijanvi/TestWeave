import unittest

from app.rag.document_processor import DocumentProcessor


class TestFunctionContextEnrichment(unittest.TestCase):

    def test_function_context_precedes_implementation(self):
        documents = self.processor.create_documents(self.knowledge)

        predict_document = next(
            document
            for document in documents
            if document.metadata.get("source_type") == "functions"
            and document.metadata.get("record_index") == 0
        )

        content = predict_document.page_content

        context_position = content.index(
            "Related application context:"
        )

        implementation_position = content.index(
            "Function implementation:"
        )

        source_position = content.index(
            "def predict(): return model.predict(features)"
        )

        self.assertLess(context_position, implementation_position)
        self.assertLess(implementation_position, source_position)

    def setUp(self):
        self.processor = DocumentProcessor()

        self.knowledge = {
            "application": {
                "name": "owner/example",
                "description": "An application for cattle disease prediction.",
            },
            "functions": [
                {
                    "name": "predict",
                    "file_path": "app.py",
                    "source_code": "def predict(): return model.predict(features)",
                },
                {
                    "name": "contact",
                    "file_path": "app.py",
                    "source_code": "def contact(): return 'OK'",
                },
            ],
            "routes": [
                {
                    "path": "/predict",
                    "methods": ["GET", "POST"],
                    "function": "predict",
                },
                {
                    "path": "/contact",
                    "methods": ["GET", "POST"],
                    "function": "contact",
                },
            ],
            "form_route_mappings": [
                {
                    "backend_function": "predict",
                    "backend_path": "/predict",
                    "template": "templates/predict.html",
                    "mapping_status": "matched",
                    "fields": [
                        {"name": "age"},
                        {"name": "breed"},
                        {"name": "symptom"},
                    ],
                },
            ],
            "data_flows": [
                {
                    "backend_function": "predict",
                    "backend_variable": "prediction",
                    "frontend_variable": "prediction",
                    "mapping_status": "matched",
                },
            ],
            "rendered_templates": [
                {
                    "function": "predict",
                    "template": "predict.html",
                    "context_variables": [
                        {"name": "prediction", "source": "prediction[0]"},
                    ],
                },
            ],
        }

    def test_enriches_function_with_related_application_context(self):
        documents = self.processor.create_documents(self.knowledge)

        predict_document = next(
            document
            for document in documents
            if document.metadata.get("source_type") == "functions"
            and document.metadata.get("record_index") == 0
        )

        content = predict_document.page_content

        self.assertIn("cattle disease prediction", content)
        self.assertIn("/predict", content)
        self.assertIn("GET", content)
        self.assertIn("POST", content)
        self.assertIn("age", content)
        self.assertIn("breed", content)
        self.assertIn("symptom", content)
        self.assertIn("prediction", content)
        self.assertIn("predict.html", content)

    def test_does_not_add_prediction_context_to_unrelated_function(self):
        documents = self.processor.create_documents(self.knowledge)

        contact_document = next(
            document
            for document in documents
            if document.metadata.get("source_type") == "functions"
            and document.metadata.get("record_index") == 1
        )

        self.assertNotIn(
            "cattle disease prediction",
            contact_document.page_content,
        )
        self.assertNotIn(
            "/predict",
            contact_document.page_content,
        )
        self.assertNotIn(
            "Application description:",
            contact_document.page_content,
        )

    def test_enriches_route_with_related_function_context(self):
        documents = self.processor.create_documents(self.knowledge)

        predict_route = next(
            document
            for document in documents
            if document.metadata.get("source_type") == "routes"
            and document.metadata.get("record_index") == 0
        )

        content = predict_route.page_content

        self.assertIn("cattle disease prediction", content)
        self.assertIn("/predict", content)
        self.assertIn("predict", content)
        self.assertIn("GET", content)
        self.assertIn("POST", content)
        self.assertIn("predict.html", content)
        self.assertIn("prediction", content)

    def test_does_not_add_prediction_context_to_unrelated_route(self):
        documents = self.processor.create_documents(self.knowledge)

        contact_route = next(
            document
            for document in documents
            if document.metadata.get("source_type") == "routes"
            and document.metadata.get("record_index") == 1
        )

        content = contact_route.page_content

        self.assertNotIn("cattle disease prediction", content)
        self.assertNotIn("/predict", content)
        self.assertNotIn("Application description:", content)

    def test_does_not_modify_original_knowledge(self):
        import copy

        original = copy.deepcopy(self.knowledge)

        self.processor.create_documents(self.knowledge)

        self.assertEqual(self.knowledge, original)

    def test_only_matched_forms_are_described_as_confirmed(self):
        self.knowledge["form_route_mappings"] = [
            {
                "backend_function": "predict",
                "template": "templates/predict.html",
                "mapping_status": "matched",
                "fields": [{"name": "age"}],
            }
        ]

        documents = self.processor.create_documents(self.knowledge)

        predict_document = next(
            document
            for document in documents
            if document.metadata.get("source_type") == "functions"
            and document.metadata.get("record_index") == 0
        )

        self.assertIn(
            "Confirmed frontend form:",
            predict_document.page_content,
        )

    def test_describes_client_side_form_without_calling_it_mapped(self):
        self.knowledge["form_route_mappings"] = [
            {
                "backend_function": "predict",
                "template": "templates/predict.html",
                "mapping_status": "client_side",
                "fields": [{"name": "age"}],
            }
        ]

        documents = self.processor.create_documents(self.knowledge)

        predict_document = next(
            document
            for document in documents
            if document.metadata.get("source_type") == "functions"
            and document.metadata.get("record_index") == 0
        )

        content = predict_document.page_content

        self.assertIn("Client-side form:", content)
        self.assertNotIn("Confirmed frontend form:", content)

    def test_unverified_mapping_does_not_complete_feature_context(self):
        self.knowledge["form_route_mappings"] = [
            {
                "backend_function": "predict",
                "template": "templates/predict.html",
                "mapping_status": "unverified",
                "fields": [{"name": "age"}],
            }
        ]

        documents = self.processor.create_documents(self.knowledge)

        predict_document = next(
            document
            for document in documents
            if document.metadata.get("source_type") == "functions"
            and document.metadata.get("record_index") == 0
        )

        content = predict_document.page_content

        self.assertNotIn(
            "Application description:",
            content,
        )
        self.assertIn(
            "Unverified frontend form:",
            content,
        )


    def test_enriches_data_flow_with_natural_language_context(self):
        self.knowledge["data_flows"][0].update({
            "backend_source": "prediction[0]",
            "template": "predict.html",
            "usage_types": ["condition", "dynamic_expression"],
            "conditions": [
                {"condition": "prediction", "line": 74, "type": "if"},
            ],
            "dynamic_expressions": [
                {"expression": "prediction", "line": 76},
            ],
        })

        documents = self.processor.create_documents(self.knowledge)

        prediction_flow = next(
            document
            for document in documents
            if document.metadata.get("source_type") == "data_flows"
            and document.metadata.get("record_index") == 0
        )

        content = prediction_flow.page_content

        self.assertIn("Backend variable: prediction", content)
        self.assertIn("Frontend variable: prediction", content)
        self.assertIn("predict.html", content)
        self.assertIn("conditional", content.lower())
        self.assertIn("dynamic expression", content.lower())
        self.assertEqual(
            prediction_flow.metadata["source_type"],
            "data_flows",
        )
        self.assertEqual(prediction_flow.metadata["record_index"], 0)



    def test_route_context_does_not_leak_between_duplicate_function_names(self):
        self.knowledge["functions"] = [
            {
                "name": "predict",
                "file_path": "app/predict.py",
                "source_code": 'def predict(): return "cattle prediction"',
            },
            {
                "name": "predict",
                "file_path": "app/admin.py",
                "source_code": 'def predict(): return "admin prediction"',
            },
        ]

        self.knowledge["routes"] = [
            {
                "path": "/predict",
                "methods": ["POST"],
                "function": "predict",
                "file_path": "app/predict.py",
            },
            {
                "path": "/admin/predict",
                "methods": ["POST"],
                "function": "predict",
                "file_path": "app/admin.py",
            },
        ]

        documents = self.processor.create_documents(self.knowledge)

        admin_route = next(
            document
            for document in documents
            if document.metadata.get("source_type") == "routes"
            and document.metadata.get("record_index") == 1
        )

        content = admin_route.page_content

        self.assertIn(
            "Backend route: /admin/predict",
            content,
        )
        self.assertNotIn(
            "Backend route: /predict ",
            content,
        )


    def test_does_not_guess_function_when_duplicate_names_have_no_route_file_path(self):
        self.knowledge["functions"] = [
            {
                "name": "predict",
                "file_path": "app/predict.py",
                "source_code": "def predict(): return 'prediction'",
            },
            {
                "name": "predict",
                "file_path": "app/admin.py",
                "source_code": "def predict(): return 'admin'",
            },
        ]

        self.knowledge["routes"] = [
            {
                "path": "/predict",
                "methods": ["POST"],
                "function": "predict",
            },
        ]

        documents = self.processor.create_documents(self.knowledge)

        route_document = next(
            document
            for document in documents
            if document.metadata.get("source_type") == "routes"
        )

        self.assertNotIn(
            "Related application context:",
            route_document.page_content,
        )

if __name__ == "__main__":
    unittest.main()