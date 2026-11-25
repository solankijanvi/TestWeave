import unittest

from app.codebase.javascript_analyzer import JavaScriptAnalyzer


class TestJavaScriptAnalyzer(unittest.TestCase):

    def setUp(self):
        self.analyzer = JavaScriptAnalyzer()

    def analyze(self, content, path="static/scripts.js"):
        return self.analyzer.analyze_file({
            "path": path,
            "content": content,
        })

    def test_detects_client_side_form_submission(self):
        content = """
        const form = document.getElementById('review-form');

        form.addEventListener('submit', (event) => {
            event.preventDefault();
            const name = document.getElementById('name').value;
            document.getElementById('review-container').prepend(name);
        });
        """

        result = self.analyze(content)

        self.assertEqual(result["analysis_status"], "success")
        self.assertEqual(len(result["form_handlers"]), 1)

        handler = result["form_handlers"][0]

        self.assertEqual(handler["form_id"], "review-form")
        self.assertTrue(handler["prevents_default"])
        self.assertEqual(handler["network_requests"], [])
        self.assertEqual(handler["handling_type"], "client_side")

    def test_detects_network_submission_in_form_handler(self):
        content = """
        const form = document.getElementById('contact-form');

        form.addEventListener('submit', async (event) => {
            event.preventDefault();

            await fetch('/api/contact', {
                method: 'POST',
                body: new FormData(form)
            });
        });
        """

        result = self.analyze(content)

        handler = result["form_handlers"][0]

        self.assertEqual(handler["form_id"], "contact-form")
        self.assertTrue(handler["prevents_default"])
        self.assertIn("fetch", handler["network_requests"])
        self.assertEqual(
            handler["handling_type"],
            "javascript_submission",
        )

    def test_does_not_associate_unidentified_handler_with_a_form(self):
        content = """
        document.addEventListener('submit', (event) => {
            event.preventDefault();
        });
        """

        result = self.analyze(content)

        self.assertEqual(len(result["form_handlers"]), 1)

        handler = result["form_handlers"][0]

        self.assertIsNone(handler["form_id"])
        self.assertEqual(handler["handling_type"], "unverified")

    def test_ignores_network_calls_outside_form_handler(self):
        content = """
        fetch('/api/status');

        const form = document.getElementById('review-form');

        form.addEventListener('submit', (event) => {
            event.preventDefault();
            document.getElementById('result').textContent = 'Submitted';
        });
        """

        result = self.analyze(content)

        handler = result["form_handlers"][0]

        self.assertEqual(handler["form_id"], "review-form")
        self.assertEqual(handler["network_requests"], [])
        self.assertEqual(handler["handling_type"], "client_side")

    def test_preserves_javascript_file_path(self):
        result = self.analyze(
            """
            const form = document.getElementById('review-form');
            form.addEventListener('submit', (event) => {
                event.preventDefault();
            });
            """,
            path="static/js/reviews.js",
        )

        self.assertEqual(
            result["file_path"],
            "static/js/reviews.js",
        )

    def test_analyzes_only_javascript_files(self):
        repository_data = {
            "files": [
                {
                    "path": "static/scripts.js",
                    "content": """
                        const form = document.getElementById('review-form');
                        form.addEventListener('submit', (event) => {
                            event.preventDefault();
                        });
                    """,
                },
                {
                    "path": "templates/review.html",
                    "content": "<form id='review-form'></form>",
                },
                {
                    "path": "app.py",
                    "content": "print('hello')",
                },
            ]
        }

        result = self.analyzer.analyze_repository(repository_data)

        self.assertEqual(result["total_javascript_files"], 1)
        self.assertEqual(result["successful_files"], 1)
        self.assertEqual(result["failed_files"], 0)
        self.assertEqual(len(result["files"]), 1)
        self.assertEqual(
            result["files"][0]["file_path"],
            "static/scripts.js",
        )

    def test_aggregates_form_handlers_across_javascript_files(self):
        repository_data = {
            "files": [
                {
                    "path": "static/scripts.js",
                    "content": """
                        const form = document.getElementById('review-form');
                        form.addEventListener('submit', (event) => {
                            event.preventDefault();
                        });
                    """,
                },
                {
                    "path": "static/contact.js",
                    "content": """
                        const form = document.getElementById('contact-form');
                        form.addEventListener('submit', (event) => {
                            event.preventDefault();
                            fetch('/api/contact');
                        });
                    """,
                },
            ]
        }

        result = self.analyzer.analyze_repository(repository_data)

        self.assertEqual(result["total_javascript_files"], 2)
        self.assertEqual(result["successful_files"], 2)
        self.assertEqual(result["failed_files"], 0)
        self.assertEqual(len(result["form_handlers"]), 2)

        self.assertEqual(
            result["form_handlers"][0]["file_path"],
            "static/scripts.js",
        )
        self.assertEqual(
            result["form_handlers"][1]["file_path"],
            "static/contact.js",
        )

    def test_counts_failed_javascript_files(self):
        repository_data = {
            "files": [
                {
                    "path": "static/scripts.js",
                    "content": """
                        const form = document.getElementById('review-form');
                        form.addEventListener('submit', (event) => {
                            event.preventDefault();
                        });
                    """,
                },
                {
                    "path": "static/broken.js",
                    "content": None,
                },
            ]
        }

        result = self.analyzer.analyze_repository(repository_data)

        self.assertEqual(result["total_javascript_files"], 2)
        self.assertEqual(result["successful_files"], 1)
        self.assertEqual(result["failed_files"], 1)
        self.assertEqual(len(result["form_handlers"]), 1)

if __name__ == "__main__":
    unittest.main()