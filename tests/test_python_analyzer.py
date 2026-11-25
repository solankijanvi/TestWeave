
import unittest

from app.codebase.python_analyzer import PythonAnalyzer

class TestPythonAnalyzer(unittest.TestCase):

    def test_nested_render_template_is_attributed_only_to_inner_function(self):
        source = """
def outer():
    def inner():
        return render_template("inner.html", value=data)
    return inner()
"""

        result = PythonAnalyzer().analyze_file({
            "path": "sample.py",
            "content": source,
        })

        rendered_templates = result["rendered_templates"]

        self.assertEqual(len(rendered_templates), 1)
        self.assertEqual(rendered_templates[0]["function"], "inner")
        self.assertEqual(rendered_templates[0]["template"], "inner.html")

    def test_outer_and_inner_functions_keep_their_own_rendered_templates(self):
        source = """
def outer():
    render_template("outer.html", user=user)

    def inner():
        render_template("inner.html", value=data)

    return inner()
"""

        result = PythonAnalyzer().analyze_file({
            "path": "sample.py",
            "content": source,
        })

        actual = {
            (item["function"], item["template"])
            for item in result["rendered_templates"]
        }

        expected = {
            ("outer", "outer.html"),
            ("inner", "inner.html"),
        }

        self.assertEqual(actual, expected)

    def test_extracts_all_python_parameter_categories(self):
        source = """
def predict(request, /, threshold=0.5, *features, model="default", **options):
    pass
"""

        result = PythonAnalyzer().analyze_file({
            "path": "sample.py",
            "content": source,
        })

        function = next(
            item
            for item in result["functions"]
            if item["name"] == "predict"
        )

        self.assertEqual(
            function["parameters"],
            ["request", "threshold", "features", "model", "options"],
        )

    def test_extracts_positional_only_parameter_metadata(self):
        source = """
def predict(request, /, threshold=0.5):
    pass
"""

        result = PythonAnalyzer().analyze_file({
            "path": "sample.py",
            "content": source,
        })

        function = next(
            item
            for item in result["functions"]
            if item["name"] == "predict"
        )

        self.assertEqual(
            function["parameter_details"],
            [
                {
                    "name": "request",
                    "kind": "positional_only",
                    "annotation": None,
                    "default": None,
                },
                {
                    "name": "threshold",
                    "kind": "positional_or_keyword",
                    "annotation": None,
                    "default": "0.5",
                },
            ],
        )

    def test_extracts_parameter_annotations_defaults_and_return_annotation(self):
        source = """
def predict(
    image_path: str,
    threshold: float = 0.5,
    *features: float,
    model: str = "default",
    **options: dict
) -> dict:
    pass
"""

        result = PythonAnalyzer().analyze_file({
            "path": "sample.py",
            "content": source,
        })

        function = next(
            item
            for item in result["functions"]
            if item["name"] == "predict"
        )

        self.assertEqual(function["return_annotation"], "dict")

        self.assertEqual(
            function["parameter_details"],
            [
                {
                    "name": "image_path",
                    "kind": "positional_or_keyword",
                    "annotation": "str",
                    "default": None,
                },
                {
                    "name": "threshold",
                    "kind": "positional_or_keyword",
                    "annotation": "float",
                    "default": "0.5",
                },
                {
                    "name": "features",
                    "kind": "var_positional",
                    "annotation": "float",
                    "default": None,
                },
                {
                    "name": "model",
                    "kind": "keyword_only",
                    "annotation": "str",
                    "default": "'default'",
                },
                {
                    "name": "options",
                    "kind": "var_keyword",
                    "annotation": "dict",
                    "default": None,
                },
            ],
        )

if __name__ == "__main__":
    unittest.main()