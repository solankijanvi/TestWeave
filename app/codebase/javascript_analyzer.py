import re


class JavaScriptAnalyzer:
    """
    Performs static analysis of JavaScript form submit handlers.

    Does not execute JavaScript. Only reports evidence detected
    through supported source patterns.
    """

    FORM_REFERENCE_PATTERN = re.compile(
        r"""
        \b(?:const|let|var)\s+
        (?P<variable>[$\w]+)\s*=\s*
        document\.(?:getElementById|querySelector)\s*
        \(\s*['"](?P<selector>[^'"]+)['"]\s*\)
        """,
        re.VERBOSE,
    )

    SUBMIT_LISTENER_PATTERN = re.compile(
        r"""
        (?P<target>[$\w]+|document|window)
        \s*\.\s*addEventListener\s*
        \(\s*['"]submit['"]\s*,
        """,
        re.VERBOSE,
    )

    NETWORK_PATTERNS = {
        "fetch": re.compile(r"\bfetch\s*\("),
        "axios": re.compile(
            r"\baxios\s*\.\s*(?:get|post|put|patch|delete|request)\s*\(",
            re.IGNORECASE,
        ),
        "XMLHttpRequest": re.compile(
            r"\b(?:new\s+XMLHttpRequest\s*\(|"
            r"\.open\s*\(|\.send\s*\()"
        ),
        "sendBeacon": re.compile(r"\bsendBeacon\s*\("),
    }

    @staticmethod
    def _extract_block(content: str, opening_index: int) -> str | None:
        """
        Extract a balanced brace block while ignoring braces
        inside ordinary strings and comments.
        """

        depth = 0
        quote = None
        escaped = False
        line_comment = False
        block_comment = False

        index = opening_index

        while index < len(content):
            character = content[index]
            next_character = (
                content[index + 1]
                if index + 1 < len(content)
                else ""
            )

            if line_comment:
                if character == "\n":
                    line_comment = False

            elif block_comment:
                if character == "*" and next_character == "/":
                    block_comment = False
                    index += 1

            elif quote:
                if escaped:
                    escaped = False
                elif character == "\\":
                    escaped = True
                elif character == quote:
                    quote = None

            elif character == "/" and next_character == "/":
                line_comment = True
                index += 1

            elif character == "/" and next_character == "*":
                block_comment = True
                index += 1

            elif character in {"'", '"', "`"}:
                quote = character

            elif character == "{":
                depth += 1

            elif character == "}":
                depth -= 1

                if depth == 0:
                    return content[opening_index + 1:index]

            index += 1

        return None

    @classmethod
    def _extract_form_references(cls, content: str) -> dict:
        """Map JavaScript variables to statically identified form IDs."""

        references = {}

        for match in cls.FORM_REFERENCE_PATTERN.finditer(content):
            selector = match.group("selector")
            form_id = None

            if match.group(0).find("getElementById") != -1:
                form_id = selector
            elif selector.startswith("#"):
                form_id = selector[1:]

            if form_id:
                references[match.group("variable")] = form_id

        return references

    @classmethod
    def _detect_network_requests(cls, handler_body: str) -> list[str]:
        """Detect supported network APIs inside one handler body."""

        detected = []

        for api_name, pattern in cls.NETWORK_PATTERNS.items():
            if pattern.search(handler_body):
                detected.append(api_name)

        return detected

    @staticmethod
    def _extract_handler_body(content: str, start_index: int) -> str | None:
        """Find and extract the callback's first brace block."""

        opening_index = content.find("{", start_index)

        if opening_index == -1:
            return None

        return JavaScriptAnalyzer._extract_block(
            content,
            opening_index,
        )

    def analyze_file(self, file_info: dict) -> dict:
        """Analyze submit handlers in one JavaScript file."""

        file_path = file_info.get("path", "Unknown file")
        content = file_info.get("content", "")

        if not isinstance(content, str):
            return {
                "file_path": file_path,
                "analysis_status": "failed",
                "error": "JavaScript content must be a string.",
                "form_handlers": [],
            }

        try:
            form_references = self._extract_form_references(content)
            form_handlers = []

            for match in self.SUBMIT_LISTENER_PATTERN.finditer(content):
                target = match.group("target")

                handler_body = self._extract_handler_body(
                    content,
                    match.end(),
                )

                if handler_body is None:
                    continue

                form_id = form_references.get(target)

                prevents_default = bool(
                    re.search(
                        r"\bpreventDefault\s*\(",
                        handler_body,
                    )
                )

                network_requests = self._detect_network_requests(
                    handler_body
                )

                if form_id and network_requests:
                    handling_type = "javascript_submission"
                elif form_id and prevents_default:
                    handling_type = "client_side"
                else:
                    handling_type = "unverified"

                form_handlers.append({
                    "form_id": form_id,
                    "target_variable": (
                        target
                        if target not in {"document", "window"}
                        else None
                    ),
                    "prevents_default": prevents_default,
                    "network_requests": network_requests,
                    "handling_type": handling_type,
                })

            return {
                "file_path": file_path,
                "analysis_status": "success",
                "form_handlers": form_handlers,
            }

        except Exception as error:
            return {
                "file_path": file_path,
                "analysis_status": "failed",
                "error": str(error),
                "form_handlers": [],
            }

    def analyze_repository(self, repository_data: dict) -> dict:
        """Analyze all downloaded JavaScript files in a repository."""

        javascript_files = [
            file_info
            for file_info in repository_data.get("files", [])
            if file_info.get("path", "").lower().endswith(".js")
        ]

        file_results = [
            self.analyze_file(file_info)
            for file_info in javascript_files
        ]

        form_handlers = [
            {
                **handler,
                "file_path": file_result["file_path"],
            }
            for file_result in file_results
            if file_result["analysis_status"] == "success"
            for handler in file_result["form_handlers"]
        ]

        return {
            "total_javascript_files": len(javascript_files),
            "successful_files": sum(
                1
                for result in file_results
                if result["analysis_status"] == "success"
            ),
            "failed_files": sum(
                1
                for result in file_results
                if result["analysis_status"] == "failed"
            ),
            "form_handlers": form_handlers,
            "files": file_results,
        }
