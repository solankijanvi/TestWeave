import posixpath
from urllib.parse import urlparse


class ApplicationMapper:
    """
    Connects frontend HTML forms with backend Python routes.

    Uses explicit form actions and referenced JavaScript handlers.
    Does not execute application code.

    A template-rendering route is not assumed to handle form submission.
    """

    def map_application(
        self,
        python_analysis: dict,
        template_analysis: dict,
        javascript_analysis: dict = None,
    ) -> dict:

        routes = python_analysis.get("flask_routes", [])

        javascript_analysis = javascript_analysis or {}
        javascript_handlers = javascript_analysis.get(
            "form_handlers", []
        )

        form_mappings = []
        mapped_forms = []
        unmapped_forms = []

        for file in template_analysis.get("files", []):
            template_path = file["file_path"]
            script_references = file.get("script_references", [])

            referenced_scripts = {
                self._normalize_script_path(reference)
                for reference in script_references
            }

            for form in file.get("forms", []):
                action = form.get("action", "").strip()
                method = form.get("method", "GET").upper()
                fields = form.get("fields", [])
                form_id = form.get("id")

                mapping = {
                    "template": template_path,
                    "form_id": form_id,
                    "action": action,
                    "form_action": action,
                    "method": method,
                    "fields": fields,
                    "mapping_status": "unverified",
                    "handling_type": "unverified",
                    "mapping_reason": "",
                    "backend_function": None,
                    "backend_path": None,
                }

                # CASE 1: Find JavaScript handlers linked through
                # scripts explicitly referenced by this template.
                matching_handlers = []

                if form_id:
                    for handler in javascript_handlers:
                        handler_path = handler.get("file_path")

                        if not handler_path:
                            continue

                        normalized_handler_path = (
                            self._normalize_script_path(handler_path)
                        )

                        if (
                            normalized_handler_path in referenced_scripts
                            and handler.get("form_id") == form_id
                        ):
                            matching_handlers.append(handler)

                if matching_handlers:
                    handler = matching_handlers[0]
                    handling_type = handler.get(
                        "handling_type",
                        "unverified",
                    )

                    mapping["handling_type"] = handling_type

                    if handling_type == "client_side":
                        mapping["mapping_status"] = "client_side"
                        mapping["mapping_reason"] = (
                            "Referenced JavaScript handler prevents "
                            "native form submission; no supported "
                            "network request was detected."
                        )

                    elif handling_type == "javascript_submission":
                        mapping["mapping_status"] = (
                            "javascript_submission"
                        )
                        mapping["mapping_reason"] = (
                            "Referenced JavaScript handler contains "
                            "a detected network request."
                        )

                    else:
                        mapping["mapping_status"] = "unverified"
                        mapping["mapping_reason"] = (
                            "A referenced JavaScript handler was found, "
                            "but its submission behavior is unverified."
                        )

                # CASE 2: Resolve an explicit native form action.
                elif action:
                    endpoint = self._extract_endpoint(action)
                    mapping["endpoint"] = endpoint

                    if not endpoint:
                        mapping["mapping_status"] = "unmapped"
                        mapping["mapping_reason"] = (
                            "Could not resolve the explicit form action."
                        )

                    else:
                        matching_routes = [
                            route
                            for route in routes
                            if (
                                route.get("function") == endpoint
                                and method in route.get("methods", [])
                            )
                        ]

                        if matching_routes:
                            # Keep one mapping record per HTML form.
                            # Preserve all route candidates for traceability.
                            selected_route = matching_routes[0]

                            mapping["mapping_status"] = "matched"
                            mapping["handling_type"] = "native"
                            mapping["mapping_reason"] = (
                                "Explicit Flask url_for action matched "
                                "a backend route and HTTP method."
                            )
                            mapping["backend_function"] = (
                                selected_route.get("function")
                            )
                            mapping["backend_path"] = (
                                selected_route.get("path")
                            )
                            mapping["candidate_routes"] = [
                                {
                                    "backend_function": route.get(
                                        "function"
                                    ),
                                    "backend_path": route.get("path"),
                                }
                                for route in matching_routes
                            ]

                        else:
                            mapping["mapping_status"] = "unmapped"
                            mapping["mapping_reason"] = (
                                "No backend route matched the explicit "
                                "endpoint and HTTP method."
                            )

                # CASE 3: No conclusive submission evidence.
                else:
                    mapping["mapping_status"] = "unverified"
                    mapping["mapping_reason"] = (
                        "No explicit form action or associated "
                        "JavaScript submission handler was detected. "
                        "A template-rendering route alone does not "
                        "establish the form submission destination."
                    )

                form_mappings.append(mapping)

                if mapping["mapping_status"] == "matched":
                    mapped_forms.append(mapping)
                else:
                    unmapped_forms.append({
                        **mapping,
                        "reason": mapping["mapping_reason"],
                    })

        return {
            "total_forms": len(form_mappings),
            "mapped_forms_count": len(mapped_forms),
            "unmapped_forms_count": len(unmapped_forms),
            "mapped_forms": mapped_forms,
            "unmapped_forms": unmapped_forms,
            "form_mappings": form_mappings,
        }

    @staticmethod
    def _normalize_script_path(reference: str) -> str:
        """
        Normalize script references from HTML templates.

        Supports:
        - Repository paths
        - Root-relative URLs
        - Flask Jinja static url_for expressions
        """

        if not reference:
            return ""

        reference = reference.strip()

        # Resolve Flask's static file reference:
        # {{ url_for('static', filename='scripts.js') }}
        static_marker = "url_for('static'"
        double_quote_marker = 'url_for("static"'

        if static_marker in reference or double_quote_marker in reference:
            filename_marker = "filename="

            filename_start = reference.find(filename_marker)

            if filename_start == -1:
                return ""

            filename_value = reference[
                filename_start + len(filename_marker):
            ].strip()

            if not filename_value or filename_value[0] not in {"'", '"'}:
                return ""

            quote = filename_value[0]
            filename_end = filename_value.find(quote, 1)

            if filename_end == -1:
                return ""

            filename = filename_value[1:filename_end]

            path = posixpath.join("static", filename)

        else:
            path = urlparse(reference).path

        path = path.replace("\\", "/").lstrip("/")

        return posixpath.normpath(path)

    @staticmethod
    def _extract_endpoint(action: str) -> str | None:
        """Extract an endpoint from a Flask url_for expression."""

        if not action:
            return None

        action = action.strip()
        marker = "url_for("

        if marker not in action:
            return None

        start = action.find(marker) + len(marker)
        remaining = action[start:]

        quote_position = None

        for index, character in enumerate(remaining):
            if character in {"'", '"'}:
                quote_position = index
                break

        if quote_position is None:
            return None

        quote_character = remaining[quote_position]
        end = remaining.find(
            quote_character,
            quote_position + 1,
        )

        if end == -1:
            return None

        endpoint = remaining[quote_position + 1:end].strip()

        return endpoint or None
