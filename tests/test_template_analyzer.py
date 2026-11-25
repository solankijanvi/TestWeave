import unittest

from app.codebase.template_analyzer import TemplateAnalyzer


class TestTemplateAnalyzer(unittest.TestCase):

    def setUp(self):
        self.analyzer = TemplateAnalyzer()

    def analyze_html(self, html):
        return self.analyzer.analyze_file({
            "path": "templates/test.html",
            "content": html,
        })

    def test_extracts_form_identity_attributes(self):
        result = self.analyze_html(
            """
            <form
                id="review-form"
                name="review"
                onsubmit="return validateReview()"
                action="/reviews"
                method="post"
            >
                <input type="text" name="username">
            </form>
            """
        )

        form = result["forms"][0]

        self.assertEqual(form["id"], "review-form")
        self.assertEqual(form["name"], "review")
        self.assertEqual(
            form["onsubmit"],
            "return validateReview()",
        )

    def test_extracts_external_script_references(self):
        result = self.analyze_html(
            """
            <html>
                <head>
                    <script src="/static/scripts.js"></script>
                    <script src="/static/validation.js"></script>
                </head>
            </html>
            """
        )

        self.assertEqual(
            result["script_references"],
            [
                "/static/scripts.js",
                "/static/validation.js",
            ],
        )

    def test_ignores_inline_scripts_without_src(self):
        result = self.analyze_html(
            """
            <script>
                console.log("Hello");
            </script>
            """
        )

        self.assertEqual(result["script_references"], [])

    def test_preserves_existing_form_attributes_and_fields(self):
        result = self.analyze_html(
            """
            <form>
                <input
                    type="email"
                    name="email"
                    id="email"
                    required
                >
                <textarea
                    name="message"
                    id="message"
                    required
                ></textarea>
                <select name="category" id="category">
                    <option value="general">General</option>
                </select>
                <input type="submit" value="Submit">
            </form>
            """
        )

        form = result["forms"][0]

        self.assertEqual(form["action"], "")
        self.assertEqual(form["method"], "GET")
        self.assertEqual(
            form["enctype"],
            "application/x-www-form-urlencoded",
        )
        self.assertEqual(form["target"], "_self")

        self.assertEqual(len(form["fields"]), 4)

        self.assertTrue(form["fields"][0]["required"])
        self.assertEqual(form["fields"][0]["type"], "email")

        self.assertEqual(
            form["fields"][1]["tag"],
            "textarea",
        )

        self.assertEqual(
            form["fields"][2]["options"][0]["text"],
            "General",
        )

        self.assertEqual(
            form["fields"][3]["role"],
            "submit_control",
        )

    def test_returns_consistent_script_references_on_failure(self):
        analyzer = TemplateAnalyzer()

        # A malformed input object triggers the failure path.
        result = analyzer.analyze_file({
            "path": "templates/broken.html",
            "content": None,
        })

        self.assertEqual(result["analysis_status"], "failed")
        self.assertEqual(result["forms"], [])
        self.assertEqual(result["script_references"], [])


if __name__ == "__main__":
    unittest.main()
