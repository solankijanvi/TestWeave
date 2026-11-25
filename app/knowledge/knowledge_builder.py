from pathlib import Path
class KnowledgeBuilder:
    """
    Combines repository analysis results into
    a unified application knowledge structure.
    """
    @staticmethod
    def _extract_readme_description(files: list[dict]) -> str | None:
        """Extract the first descriptive paragraph from a README."""

        for file_info in files:
            path = file_info.get("path", "")

            if Path(path).name.lower() != "readme.md":
                continue

            content = file_info.get("content", "")

            if not isinstance(content, str):
                continue

            found_title = False
            paragraph = []

            for line in content.splitlines():
                line = line.strip()

                if not found_title:
                    if line.startswith("# "):
                        found_title = True
                    continue

                if not line:
                    if paragraph:
                        break
                    continue

                if line.startswith("#"):
                    if paragraph:
                        break
                    continue

                if line.startswith(("![", "<")):
                    continue

                paragraph.append(line)

            if paragraph:
                description = " ".join(paragraph)
                description = description.replace("**", "")
                description = description.replace("__", "")
                return description

        return None

    def build(
        self,
        repository_data: dict,
        python_result: dict,
        template_result: dict,
        mapping_result: dict,
        data_flow_result: dict,
    ) -> dict:
        """
        Build unified application knowledge
        from the outputs of existing analyzers.
        """

        knowledge = {
            "application": {
                "name": repository_data.get("repository", {}).get(
                    "full_name", "Unknown Application"
                ),
                "description": (
                    repository_data.get("repository", {}).get("description")
                    or self._extract_readme_description(
                        repository_data.get("files", [])
                    )
                ),
                "default_branch": repository_data.get("repository", {}).get(
                    "default_branch"
                ),
            },

            "repository": {
                "total_files_discovered": repository_data.get(
                    "total_files_discovered", 0
                ),
                "eligible_files_count": repository_data.get(
                    "eligible_files_count", 0
                ),
                "downloaded_files_count": repository_data.get(
                    "downloaded_files_count", 0
                ),
                "failed_files_count": repository_data.get(
                    "failed_files_count", 0
                ),
            },
            "statistics": {},
            "files": [],
            "routes": [],
            "functions": [],
            "classes": [],
            "forms": [],
            "form_route_mappings": [],
            "data_flows": [],
            "database_operations": [],
            "rendered_templates": [],
        }

        knowledge["files"] = [
            {
                "path": file_info.get("path"),
                "size": file_info.get("size"),
                "encoding": file_info.get("encoding"),
                "content": file_info.get("content"),
            }
            for file_info in repository_data.get("files", [])
        ]

        # Add Python analysis results.
        knowledge["routes"] = python_result.get(
            "flask_routes", []
        )

        knowledge["functions"] = [
            {
                "file_path": file_result.get("file_path"),
                **function,
            }
            for file_result in python_result.get("files", [])
            if file_result.get("analysis_status") == "success"
            for function in file_result.get("functions", [])
        ]

        knowledge["classes"] = [
            {
                "file_path": file_result.get("file_path"),
                **class_info,
            }
            for file_result in python_result.get("files", [])
            if file_result.get("analysis_status") == "success"
            for class_info in file_result.get("classes", [])
        ]

        knowledge["database_operations"] = [
            {
                "file_path": file_result.get("file_path"),
                **operation,
            }
            for file_result in python_result.get("files", [])
            if file_result.get("analysis_status") == "success"
            for operation in file_result.get("database_operations", [])
        ]

        knowledge["rendered_templates"] = python_result.get(
            "rendered_templates", []
        )


        knowledge["forms"] = [
            {
                "template": file_result.get("file_path"),
                **form,
            }
            for file_result in template_result.get("files", [])
            if file_result.get("analysis_status") == "success"
            for form in file_result.get("forms", [])
        ]

        knowledge["form_route_mappings"] = [
            {
                **form,
                "mapping_status": form.get("mapping_status", "matched"),
            }
            for form in mapping_result.get("mapped_forms", [])
        ] + [
            {
                **form,
                "mapping_status": form.get("mapping_status", "unmapped"),
            }
            for form in mapping_result.get("unmapped_forms", [])
        ]

        knowledge["data_flows"] = [
            {
                **flow,
                "mapping_status": "matched",
            }
            for flow in data_flow_result.get("mapped_flows", [])
        ] + [
            {
                **flow,
                "mapping_status": "unmapped",
            }
            for flow in data_flow_result.get("unmapped_flows", [])
        ]

        mapping_statuses = (
            "matched",
            "client_side",
            "javascript_submission",
            "unmapped",
            "unverified",
        )

        form_mapping_status_counts = {
            status: sum(
                1
                for form in knowledge["form_route_mappings"]
                if form.get("mapping_status") == status
            )
            for status in mapping_statuses
        }

        knowledge["statistics"] = {
            "downloaded_files": len(knowledge["files"]),
            "total_routes": len(knowledge["routes"]),
            "total_functions": len(knowledge["functions"]),
            "total_classes": len(knowledge["classes"]),
            "total_forms": len(knowledge["forms"]),
            "mapped_forms": len(mapping_result.get("mapped_forms", [])),
            "unmapped_forms": len(mapping_result.get("unmapped_forms", [])),
            "matched_data_flows": len(data_flow_result.get("mapped_flows", [])),
                        "form_mapping_status_counts": form_mapping_status_counts,
            "unmapped_data_flows": len(data_flow_result.get("unmapped_flows", [])),
            "total_detected_operations": len(
                knowledge["database_operations"]
            ),
            "database_candidate_operations": sum(
                1
                for operation in knowledge["database_operations"]
                if operation.get("classification") == "database_candidate"
            ),
            "non_database_operations": sum(
                1
                for operation in knowledge["database_operations"]
                if operation.get("classification") == "non_database"
            ),
            "unknown_operations": sum(
                1
                for operation in knowledge["database_operations"]
                if operation.get("classification") == "unknown"
            ),
            "render_template_calls": len(knowledge["rendered_templates"]),
        }


        return knowledge
