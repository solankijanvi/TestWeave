
import re


class DataFlowMapper:
    """
    Connects backend template context variables
    with frontend Jinja template variables.

    Detects:
    1. Loop iterable usage.
    2. Conditional usage.
    3. Dynamic expression usage.

    Uses static analysis. Does not execute application code.
    """

    def map_data_flow(
        self,
        python_analysis: dict,
        template_analysis: dict,
    ) -> dict:

        rendered_templates = python_analysis.get(
            "rendered_templates", []
        )

        template_files = template_analysis.get("files", [])

        mapped_flows = []
        unmapped_flows = []

        for rendered_template in rendered_templates:

            template_name = rendered_template["template"]
            backend_function = rendered_template["function"]

            context_variables = rendered_template.get(
                "context_variables", []
            )

            matching_files = [
                file
                for file in template_files
                if (
                    file["file_path"].endswith("/" + template_name)
                    or file["file_path"] == "templates/" + template_name
                    or file["file_path"] == template_name
                )
            ]

            if not matching_files:
                unmapped_flows.append({
                    "template": template_name,
                    "backend_function": backend_function,
                    "reason": "Template analysis data not found.",
                })
                continue

            for file in matching_files:

                jinja_analysis = file.get("jinja_analysis", {})

                loops = jinja_analysis.get("loops", [])
                conditions = jinja_analysis.get("conditions", [])
                expressions = jinja_analysis.get(
                    "dynamic_expressions", []
                )

                for context_variable in context_variables:

                    backend_variable = context_variable["name"]

                    matching_loops = [
                        loop
                        for loop in loops
                        if loop["iterable"] == backend_variable
                    ]

                    matching_conditions = [
                        condition
                        for condition in conditions
                        if (
                            condition["type"] in {"if", "elif"}
                            and self._references_variable(
                                condition["condition"],
                                backend_variable,
                            )
                        )
                    ]

                    matching_expressions = [
                        expression
                        for expression in expressions
                        if self._references_variable(
                            expression["expression"],
                            backend_variable,
                        )
                    ]

                    usage_types = []

                    if matching_loops:
                        usage_types.append("loop")

                    if matching_conditions:
                        usage_types.append("condition")

                    if matching_expressions:
                        usage_types.append("dynamic_expression")

                    flow_details = {
                        "template": template_name,
                        "backend_function": backend_function,
                        "backend_variable": backend_variable,
                        "backend_source": context_variable["source"],
                        "frontend_variable": backend_variable,
                        "usage_types": usage_types,
                        "loops": matching_loops,
                        "conditions": matching_conditions,
                        "dynamic_expressions": matching_expressions,
                    }

                    if matching_loops:
                        flow_details["frontend_iterable"] = (
                            matching_loops[0]["iterable"]
                        )
                        flow_details["loop_variable"] = (
                            matching_loops[0]["variable"]
                        )

                    if usage_types:
                        flow_details["mapping_status"] = "matched"
                        mapped_flows.append(flow_details)

                    else:
                        unmapped_flows.append({
                            "template": template_name,
                            "backend_function": backend_function,
                            "backend_variable": backend_variable,
                            "backend_source": context_variable["source"],
                            "reason": (
                                "No matching Jinja loop, condition, "
                                "or dynamic expression found."
                            ),
                        })

        return {
            "total_mapped_flows": len(mapped_flows),
            "total_unmapped_flows": len(unmapped_flows),
            "mapped_flows": mapped_flows,
            "unmapped_flows": unmapped_flows,
        }

    @staticmethod
    def _references_variable(
        expression: str | None,
        variable: str,
    ) -> bool:
        """Check whether a Jinja expression references a variable."""

        if not expression:
            return False

        pattern = rf"\b{re.escape(variable)}\b"

        return re.search(pattern, expression) is not None
