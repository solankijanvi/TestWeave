
import json
from pathlib import Path
from typing import Any

from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter


class DocumentProcessor:
    """
    Converts TestWeave application knowledge into LangChain documents
    and splits them into smaller chunks for RAG retrieval.
    """

    def __init__(
        self,
        chunk_size: int = 1000,
        chunk_overlap: int = 150,
    ) -> None:
        if chunk_size <= 0:
            raise ValueError("chunk_size must be greater than zero.")

        if chunk_overlap < 0:
            raise ValueError("chunk_overlap cannot be negative.")

        if chunk_overlap >= chunk_size:
            raise ValueError(
                "chunk_overlap must be smaller than chunk_size."
            )

        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
        )

    def load_knowledge(self, file_path: str | Path) -> dict[str, Any]:
        """Load application knowledge from a JSON file."""

        path = Path(file_path)

        if not path.exists():
            raise FileNotFoundError(f"Knowledge file not found: {path}")

        with path.open("r", encoding="utf-8") as file:
            knowledge = json.load(file)

        if not isinstance(knowledge, dict):
            raise ValueError("Application knowledge must be a JSON object.")

        return knowledge


    def create_document(
        self,
        record: dict[str, Any],
        source_type: str,
        record_index: int,
    ) -> Document:
        """Convert one knowledge record into a LangChain Document."""

        if not isinstance(record, dict):
            raise TypeError("Each knowledge record must be a dictionary.")

        if source_type == "files":
            content = record.get("content", "")
            source_path = record.get("path", "unknown")

            if not isinstance(content, str) or not content.strip():
                raise ValueError(f"Empty source file content: {source_path}")

            page_content = f"Source file: {source_path}\n\n{content}"

        else:
            collection_name = source_type.replace("_", " ")

            page_content = (
                f"Knowledge type: {collection_name}\n\n"
                + json.dumps(
                    record,
                    ensure_ascii=False,
                    indent=2,
                )
            )

        metadata = {
            "source_type": source_type,
            "record_index": record_index,
        }

        provenance_fields = [
            "path",
            "file_path",
            "template",
            "function",
            "backend_function",
            "backend_path",
            "endpoint",
            "line",
            "mapping_status",
        ]

        for field in provenance_fields:
            value = record.get(field)

            if isinstance(value, (str, int, float, bool)):
                metadata[field] = value

        return Document(
            page_content=page_content,
            metadata=metadata,
        )


    @staticmethod
    def _build_data_flow_context(
        flow_record: dict[str, Any],
    ) -> str | None:
        """Describe a recorded backend-to-frontend data flow."""

        lines = []

        backend_function = flow_record.get("backend_function")
        backend_variable = flow_record.get("backend_variable")
        backend_source = flow_record.get("backend_source")
        frontend_variable = flow_record.get("frontend_variable")
        template = flow_record.get("template")

        if backend_function:
            lines.append(
                f"Backend function: {backend_function}"
            )

        if backend_variable:
            lines.append(
                f"Backend variable: {backend_variable}"
            )

        if backend_source:
            lines.append(
                f"Backend source expression: {backend_source}"
            )

        if frontend_variable:
            lines.append(
                f"Frontend variable: {frontend_variable}"
            )

        if template:
            lines.append(
                f"Frontend template: {template}"
            )

        usage_types = flow_record.get("usage_types", [])

        if isinstance(usage_types, list):
            usage_descriptions = {
                "condition": "conditional usage",
                "dynamic_expression": "dynamic expression",
                "loop": "loop usage",
            }

            for usage_type in usage_types:
                description = usage_descriptions.get(usage_type)

                if description and description not in lines:
                    lines.append(
                        f"Frontend usage: {description}"
                    )

        conditions = flow_record.get("conditions", [])

        if isinstance(conditions, list):
            for condition in conditions:
                if not isinstance(condition, dict):
                    continue

                line_number = condition.get("line")

                if line_number is not None:
                    lines.append(
                        f"Conditional usage occurs at template line "
                        f"{line_number}."
                    )

        dynamic_expressions = flow_record.get(
            "dynamic_expressions",
            [],
        )

        if isinstance(dynamic_expressions, list):
            for expression in dynamic_expressions:
                if not isinstance(expression, dict):
                    continue

                line_number = expression.get("line")

                if line_number is not None:
                    lines.append(
                        f"Dynamic expression occurs at template line "
                        f"{line_number}."
                    )

        return "\n".join(lines) if lines else None

    @staticmethod
    def _normalize_file_path(file_path: str) -> str:
        """Normalize file paths for reliable cross-platform comparison."""

        return file_path.replace("\\", "/").strip("/").casefold()

    @classmethod
    def _matches_function(
        cls,
        record: dict[str, Any],
        function_record: dict[str, Any],
        function_key: str,
        knowledge: dict[str, Any],
    ) -> bool:
        """Match a related record to a function without ambiguous names."""

        function_name = function_record.get("name")

        if not function_name or record.get(function_key) != function_name:
            return False

        function_path = function_record.get("file_path")
        record_path = record.get("file_path")

        # When both paths exist, require an exact normalized path match.
        if function_path and record_path:
            return (
                cls._normalize_file_path(function_path)
                == cls._normalize_file_path(record_path)
            )

        # Name-only matching is safe only when the name is unique.
        matching_functions = [
            function
            for function in knowledge.get("functions", [])
            if function.get("name") == function_name
        ]

        return len(matching_functions) == 1


    @classmethod
    def _build_function_context(
        cls,
        function_record: dict[str, Any],
        knowledge: dict[str, Any],
    ) -> str | None:
        """Build context from records explicitly related to a function."""

        function_name = function_record.get("name")

        if not function_name:
            return None

        routes = [
            route
            for route in knowledge.get("routes", [])
            if cls._matches_function(
                route,
                function_record,
                "function",
                knowledge,
            )
        ]

        if not routes:
            return None

        related_mappings = [
            mapping
            for mapping in knowledge.get("form_route_mappings", [])
            if cls._matches_function(
                mapping,
                function_record,
                "backend_function",
                knowledge,
            )
        ]

        related_flows = [
            flow
            for flow in knowledge.get("data_flows", [])
            if cls._matches_function(
                flow,
                function_record,
                "backend_function",
                knowledge,
            )
        ]

        related_templates = [
            rendered
            for rendered in knowledge.get("rendered_templates", [])
            if cls._matches_function(
                rendered,
                function_record,
                "function",
                knowledge,
            )
        ]

        lines = []
        application = knowledge.get("application", {})

        if application.get("name"):
            lines.append(f"Application: {application['name']}")

        confirmed_mappings = [
            mapping
            for mapping in related_mappings
            if mapping.get("mapping_status") == "matched"
        ]

        has_complete_feature_context = (
            bool(confirmed_mappings)
            and bool(related_flows)
            and bool(related_templates)
        )

        if (
            has_complete_feature_context
            and application.get("description")
        ):
            lines.append(
                f"Application description: {application['description']}"
            )

        for route in routes:
            methods = ", ".join(route.get("methods", []))
            lines.append(
                f"Backend route: {route.get('path', 'Unknown path')} "
                f"(HTTP methods: {methods})"
            )

        mapping_labels = {
            "matched": "Confirmed frontend form",
            "client_side": "Client-side form",
            "javascript_submission": "JavaScript-submitted form",
            "unmapped": "Unmapped frontend form",
            "unverified": "Unverified frontend form",
        }

        for mapping in related_mappings:
            status = mapping.get("mapping_status", "unverified")

            label = mapping_labels.get(
                status,
                "Frontend form with unknown mapping status",
            )

            lines.append(
                f"{label}: {mapping.get('template', 'Unknown template')}"
            )

            for field in mapping.get("fields", []):
                field_name = field.get("name")

                if field_name:
                    lines.append(f"Form input field: {field_name}")

        for flow in related_flows:
            backend_variable = flow.get("backend_variable")
            frontend_variable = flow.get("frontend_variable")

            if backend_variable or frontend_variable:
                lines.append(
                    "Data flow: "
                    f"backend variable '{backend_variable}' "
                    f"is mapped to frontend variable '{frontend_variable}'"
                )

        for rendered in related_templates:
            lines.append(
                f"Rendered template: {rendered.get('template', 'Unknown template')}"
            )

            for variable in rendered.get("context_variables", []):
                variable_name = variable.get("name")
                variable_source = variable.get("source")

                if variable_name:
                    lines.append(
                        f"Template context variable: {variable_name} "
                        f"(source: {variable_source})"
                    )

        return "\n".join(lines)

    def create_documents(
        self,
        knowledge: dict[str, Any],
    ) -> list[Document]:
        """Convert all supported knowledge collections into documents."""

        documents = []

        collections = [
            "files",
            "routes",
            "functions",
            "classes",
            "forms",
            "form_route_mappings",
            "data_flows",
            "database_operations",
            "rendered_templates",
        ]

        for collection in collections:
            records = knowledge.get(collection, [])

            if not isinstance(records, list):
                raise ValueError(
                    f"Expected '{collection}' to contain a list."
                )

            for index, record in enumerate(records):
                try:

                    document = self.create_document(
                        record=record,
                        source_type=collection,
                        record_index=index,
                    )


                    if collection == "functions":
                        context = self._build_function_context(
                            function_record=record,
                            knowledge=knowledge,
                        )

                        if context:
                            function_name = record.get(
                                "name",
                                "Unknown",
                            )

                            file_path = record.get(
                                "file_path",
                                "Unknown",
                            )

                            document.page_content = (
                                f"Function: {function_name}\n"
                                f"File: {file_path}\n\n"
                                "Related application context:\n"
                                f"{context}\n\n"
                                "Function implementation:\n"
                                f"{document.page_content}"
                            )

                    elif collection == "routes":
                        related_function = next(
                            (
                                function
                                for function in knowledge.get("functions", [])
                                if self._matches_function(
                                    record,
                                    function,
                                    "function",
                                    knowledge,
                                )
                            ),
                            None,
                        )

                        if related_function:
                            context = self._build_function_context(
                                function_record=related_function,
                                knowledge=knowledge,
                            )

                            if context:
                                document.page_content += (
                                    "\n\nRelated application context:\n"
                                    + context
                                )

                    elif collection == "data_flows":
                        context = self._build_data_flow_context(record)

                        if context:
                            document.page_content = (
                                "Data flow context:\n"
                                f"{context}\n\n"
                                "Structured data-flow evidence:\n"
                                f"{document.page_content}"
                            )

                    documents.append(document)

                except (TypeError, ValueError) as error:
                    raise ValueError(
                        f"Failed to process {collection}[{index}]: {error}"
                    ) from error

        return documents


    def split_documents(
        self,
        documents: list[Document],
    ) -> list[Document]:
        """Split large source documents while preserving structured records."""

        chunks = []

        for document in documents:
            # Keep structured knowledge records intact.
            if document.metadata["source_type"] != "files":
                document.metadata["chunk_index"] = 0
                chunks.append(document)
                continue

            # Split source files into smaller chunks.
            document_chunks = self.text_splitter.split_documents(
                [document]
            )

            for chunk_index, chunk in enumerate(document_chunks):
                chunk.metadata["chunk_index"] = chunk_index
                chunks.append(chunk)

        return chunks