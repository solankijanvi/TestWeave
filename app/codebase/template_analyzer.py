import ast
import re
from html.parser import HTMLParser


class FormParser(HTMLParser):
    """Extract forms and their fields from an HTML template."""

    def __init__(self):
        super().__init__(convert_charrefs=True)

        self.forms = []
        self.script_references = []
        self.current_form = None
        self.current_select = None
        self.current_textarea = None

    def handle_starttag(self, tag, attrs):
        attributes = dict(attrs)

        if tag == "script" and attributes.get("src"):
            self.script_references.append(attributes["src"])

        if tag == "form":
            self.current_form = {
                "id": attributes.get("id"),
                "name": attributes.get("name"),
                "onsubmit": attributes.get("onsubmit"),
                "action": attributes.get("action", ""),
                "method": attributes.get("method", "GET").upper(),
                "enctype": attributes.get(
                    "enctype",
                    "application/x-www-form-urlencoded",
                ),
                "target": attributes.get("target", "_self"),
                "fields": [],
            }

        elif self.current_form is not None:

            if tag == "input":
                input_type = attributes.get("type", "text")
                field_name = attributes.get("name")

                self.current_form["fields"].append({
                    "tag": "input",
                    "name": field_name,
                    "id": attributes.get("id"),
                    "type": input_type,
                    "required": "required" in attributes,
                    "is_dynamic": (
                        field_name is not None
                        and ("{{" in field_name or "{%" in field_name)
                    ),
                    "role": (
                        "submit_control"
                        if input_type in {"submit", "button", "image"}
                        else "data_field"
                    ),
                })

            elif tag == "textarea":
                self.current_textarea = {
                    "tag": "textarea",
                    "name": attributes.get("name"),
                    "id": attributes.get("id"),
                    "required": "required" in attributes,
                }

            elif tag == "select":
                self.current_select = {
                    "tag": "select",
                    "name": attributes.get("name"),
                    "id": attributes.get("id"),
                    "required": "required" in attributes,
                    "options": [],
                }

            elif tag == "option" and self.current_select is not None:
                option_value = attributes.get("value")

                self.current_select["options"].append({
                    "value": option_value,
                    "text": "",
                    "is_dynamic": (
                        option_value is not None
                        and ("{{" in option_value or "{%" in option_value)
                    ),
                })
    def handle_data(self, data):
        if self.current_select is not None:
            if self.current_select["options"]:
                cleaned_data = re.sub(
                    r"{%.*?%}",
                    "",
                    data,
                    flags=re.DOTALL,
                )

                self.current_select["options"][-1]["text"] += (
                    cleaned_data.strip()
                )
    def handle_endtag(self, tag):

        if tag == "textarea" and self.current_textarea is not None:
            self.current_form["fields"].append(self.current_textarea)
            self.current_textarea = None

        elif tag == "select" and self.current_select is not None:
            self.current_form["fields"].append(self.current_select)
            self.current_select = None

        elif tag == "form" and self.current_form is not None:
            self.forms.append(self.current_form)
            self.current_form = None


class TemplateAnalyzer:
    """
    Analyses HTML templates without executing them.

    Extracts form actions, methods and input fields.
    """

    def analyze_file(self, file_info: dict) -> dict:
        path = file_info["path"]
        source = file_info["content"]

        parser = FormParser()
        jinja_analyzer = JinjaAnalyzer()

        try:
            parser.feed(source)
            parser.close()

            return {
                "script_references": parser.script_references,
                "file_path": path,
                "analysis_status": "success",
                "forms_count": len(parser.forms),
                "forms": parser.forms,
                "jinja_analysis": jinja_analyzer.analyze(source),
            }

        except Exception as exc:
            return {
                "file_path": path,
                "analysis_status": "failed",
                "forms_count": 0,
                "forms": [],
                "script_references": [],
                "error": str(exc),
            }

    def analyze_repository(self, repository_data: dict) -> dict:
        analyzed_files = []

        for file_info in repository_data.get("files", []):
            path = file_info["path"].lower()

            if not path.endswith((".html", ".htm")):
                continue

            analyzed_files.append(self.analyze_file(file_info))

        all_forms = [
            form
            for file in analyzed_files
            for form in file["forms"]
        ]

        return {
            "html_files_analyzed": len(analyzed_files),
            "successful_files": sum(
                file["analysis_status"] == "success"
                for file in analyzed_files
            ),
            "total_forms": len(all_forms),
            "files": analyzed_files,
        }

class JinjaAnalyzer:
    """Extract Jinja loops, conditions and dynamic expressions."""

    TOKEN_PATTERN = re.compile(
        r"{%\s*(for|endfor|if|elif|else|endif)\b(.*?)%}",
        re.DOTALL,
    )

    def analyze(self, source: str) -> dict:
        loops = []
        conditions = []
        loop_stack = []

        for match in self.TOKEN_PATTERN.finditer(source):
            tag = match.group(1)
            expression = match.group(2).strip()
            line = source.count("\n", 0, match.start()) + 1

            if tag == "for":
                loop_match = re.match(
                    r"(\w+)\s+in\s+(.+)",
                    expression,
                    re.DOTALL,
                )

                if not loop_match:
                    continue

                variable = loop_match.group(1)
                iterable = loop_match.group(2).strip()

                loop = {
                    "variable": variable,
                    "iterable": iterable,
                    "line": line,
                    "end_line": None,
                    "parent_loop": (
                        loop_stack[-1]["variable"]
                        if loop_stack else None
                    ),
                    "iteration_count": self._get_iteration_count(
                        iterable
                    ),
                }

                loops.append(loop)
                loop_stack.append(loop)

            elif tag == "endfor":
                if loop_stack:
                    loop_stack[-1]["end_line"] = line
                    loop_stack.pop()

            elif tag == "if":
                conditions.append({
                    "condition": expression,
                    "line": line,
                    "type": "if",
                })

            elif tag in {"elif", "else"}:
                conditions.append({
                    "condition": expression or None,
                    "line": line,
                    "type": tag,
                })

        dynamic_expressions = [
            {
                "expression": match.group(1).strip(),
                "line": source.count("\n", 0, match.start()) + 1,
            }
            for match in re.finditer(r"{{(.*?)}}", source, re.DOTALL)
        ]

        return {
            "loops": loops,
            "conditions": conditions,
            "dynamic_expressions": dynamic_expressions,
            "total_loops": len(loops),
            "total_conditions": len(conditions),
        }

    @staticmethod
    def _get_iteration_count(iterable: str):
        """Calculate iteration count for literal range() expressions."""

        match = re.fullmatch(
            r"range\((.*)\)",
            iterable.strip(),
        )

        if not match:
            return None

        try:
            arguments = ast.literal_eval(
                "(" + match.group(1) + ",)"
                if "," not in match.group(1)
                else "(" + match.group(1) + ")"
            )

            if not isinstance(arguments, tuple):
                arguments = (arguments,)

            if not all(type(value) is int for value in arguments):
                return None

            return len(range(*arguments))

        except (ValueError, SyntaxError, TypeError):
            return None
