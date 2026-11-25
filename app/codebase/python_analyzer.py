import ast

class PythonAnalyzer:
    """
    Analyses Python source files without executing them.

    Extracts structural information such as:
    - Imports
    - Functions and parameters
    - Classes and methods
    - Flask-style routes
    - Request references
    - Basic database-operation evidence
    """

    DATABASE_METHODS = {
        "add",
        "add_all",
        "commit",
        "connect",
        "delete",
        "execute",
        "filter",
        "filter_by",
        "first",
        "all",
        "get",
        "query",
        "update",
        "flush",
    }

    REQUEST_ATTRIBUTES = {
        "form",
        "args",
        "json",
        "files",
        "get_json",
        "values",
        "data",
    }

    HTTP_METHODS = {
        "get",
        "post",
        "put",
        "patch",
        "delete",
        "options",
        "head",
    }

    def analyze_file(self, file_info: dict) -> dict:
        """Analyse one downloaded Python file."""

        path = file_info["path"]
        source = file_info["content"]

        try:
            tree = ast.parse(source, filename=path)

        except SyntaxError as exc:
            return {
                "file_path": path,
                "analysis_status": "syntax_error",
                "line_count": len(source.splitlines()),
                "imports": [],
                "functions": [],
                "classes": [],
                "flask_routes": [],
                "request_references": [],
                "database_operations": [],
                "syntax_error": {
                    "message": exc.msg,
                    "line": exc.lineno,
                },
            }

        result = {
            "file_path": path,
            "analysis_status": "success",
            "line_count": len(source.splitlines()),
            "imports": self._extract_imports(tree),
            "functions": self._extract_functions(tree, source),
            "classes": self._extract_classes(tree),
            "flask_routes": self._extract_routes(tree),
            "rendered_templates": self._extract_rendered_templates(tree),
            "request_references": self._extract_request_references(tree),
            "database_operations": self._extract_database_operations(tree),
            "syntax_error": None,
        }

        return result

    def analyze_repository(self, repository_data: dict) -> dict:
        """Analyse all eligible Python files in a loaded repository."""

        analyzed_files = []

        for file_info in repository_data.get("files", []):
            if not file_info["path"].lower().endswith(".py"):
                continue

            analyzed_files.append(self.analyze_file(file_info))

        successful_files = [
            item for item in analyzed_files
            if item["analysis_status"] == "success"
        ]

        syntax_error_files = [
            item for item in analyzed_files
            if item["analysis_status"] == "syntax_error"
        ]

        all_routes = [
            route
            for item in successful_files
            for route in item["flask_routes"]
        ]

        all_rendered_templates = [
            template
            for item in successful_files
            for template in item["rendered_templates"]
        ]

        return {
            "repository": repository_data.get("repository", {}),
            "python_files_analyzed": len(analyzed_files),
            "successful_files": len(successful_files),
            "files_with_syntax_errors": len(syntax_error_files),
            "total_functions": sum(
                len(item["functions"]) for item in successful_files
            ),
            "total_classes": sum(
                len(item["classes"]) for item in successful_files
            ),
            "total_routes": len(all_routes),
            "flask_routes": all_routes,
            "rendered_templates": all_rendered_templates,
            "files": analyzed_files,
        }

    def _extract_imports(self, tree: ast.AST) -> list:
        imports = []

        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    imports.append({
                        "module": alias.name,
                        "imported_name": None,
                        "line": node.lineno,
                    })

            elif isinstance(node, ast.ImportFrom):
                for alias in node.names:
                    imports.append({
                        "module": node.module or "",
                        "imported_name": alias.name,
                        "line": node.lineno,
                    })

        return imports

    def _extract_functions(
        self,
        tree: ast.AST,
        source: str,
    ) -> list:
        """Extract function metadata and complete source code."""

        functions = []

        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                parameters = [
                    argument.arg
                    for argument in (
                        node.args.posonlyargs
                        + node.args.args
                    )
                ]

                if node.args.vararg:
                    parameters.append(node.args.vararg.arg)

                parameters.extend(
                    argument.arg
                    for argument in node.args.kwonlyargs
                )

                if node.args.kwarg:
                    parameters.append(node.args.kwarg.arg)

                positional_defaults = (
                    [None] * (
                        len(node.args.posonlyargs)
                        + len(node.args.args)
                        - len(node.args.defaults)
                    )
                    + node.args.defaults
                )

                parameter_details = []

                positional_arguments = (
                    [
                        (argument, "positional_only")
                        for argument in node.args.posonlyargs
                    ]
                    + [
                        (argument, "positional_or_keyword")
                        for argument in node.args.args
                    ]
                )

                for index, (argument, kind) in enumerate(positional_arguments):
                    default = positional_defaults[index]

                    parameter_details.append({
                        "name": argument.arg,
                        "kind": kind,
                        "annotation": (
                            ast.unparse(argument.annotation)
                            if argument.annotation
                            else None
                        ),
                        "default": (
                            ast.unparse(default)
                            if default is not None
                            else None
                        ),
                    })

                if node.args.vararg:
                    argument = node.args.vararg
                    parameter_details.append({
                        "name": argument.arg,
                        "kind": "var_positional",
                        "annotation": (
                            ast.unparse(argument.annotation)
                            if argument.annotation
                            else None
                        ),
                        "default": None,
                    })

                for argument, default in zip(
                    node.args.kwonlyargs,
                    node.args.kw_defaults,
                ):
                    parameter_details.append({
                        "name": argument.arg,
                        "kind": "keyword_only",
                        "annotation": (
                            ast.unparse(argument.annotation)
                            if argument.annotation
                            else None
                        ),
                        "default": (
                            ast.unparse(default)
                            if default is not None
                            else None
                        ),
                    })

                if node.args.kwarg:
                    argument = node.args.kwarg
                    parameter_details.append({
                        "name": argument.arg,
                        "kind": "var_keyword",
                        "annotation": (
                            ast.unparse(argument.annotation)
                            if argument.annotation
                            else None
                        ),
                        "default": None,
                    })


                functions.append({
                    "name": node.name,
                    "parameters": parameters,
                    "parameter_details": parameter_details,
                    "return_annotation": (
                        ast.unparse(node.returns)
                        if node.returns
                        else None
                    ),
                    "line": node.lineno,
                    "end_line": node.end_lineno,
                    "is_async": isinstance(node, ast.AsyncFunctionDef),
                    "decorators": [
                        self._get_node_name(decorator)
                        for decorator in node.decorator_list
                    ],
                    "source_code": ast.get_source_segment(source, node),
                })

        return functions

    def _extract_classes(self, tree: ast.AST) -> list:
        classes = []

        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                methods = []

                for child in node.body:
                    if isinstance(
                        child,
                        (ast.FunctionDef, ast.AsyncFunctionDef),
                    ):
                        methods.append({
                            "name": child.name,
                            "line": child.lineno,
                            "end_line": child.end_lineno,
                        })

                classes.append({
                    "name": node.name,
                    "bases": [
                        self._get_node_name(base)
                        for base in node.bases
                    ],
                    "line": node.lineno,
                    "methods": methods,
                })

        return classes

    def _extract_routes(self, tree: ast.AST) -> list:
        routes = []

        for node in ast.walk(tree):
            if not isinstance(
                node,
                (ast.FunctionDef, ast.AsyncFunctionDef),
            ):
                continue

            for decorator in node.decorator_list:
                route = self._parse_route_decorator(
                    decorator,
                    node.name,
                )

                if route:
                    routes.append(route)

        return routes

    def _parse_route_decorator(
        self,
        decorator: ast.AST,
        function_name: str,
    ) -> dict | None:
        if not isinstance(decorator, ast.Call):
            return None

        if not isinstance(decorator.func, ast.Attribute):
            return None

        decorator_name = decorator.func.attr.lower()

        if decorator_name != "route" and decorator_name not in self.HTTP_METHODS:
            return None

        if not decorator.args:
            return None

        route_path = decorator.args[0]

        if not isinstance(route_path, ast.Constant):
            return None

        if not isinstance(route_path.value, str):
            return None

        if decorator_name == "route":
            methods = ["GET"]

            for keyword in decorator.keywords:
                if keyword.arg == "methods":
                    if isinstance(keyword.value, (ast.List, ast.Tuple)):
                        methods = [
                            item.value.upper()
                            for item in keyword.value.elts
                            if isinstance(item, ast.Constant)
                            and isinstance(item.value, str)
                        ]

        else:
            methods = [decorator_name.upper()]

        return {
            "path": route_path.value,
            "methods": methods,
            "function": function_name,
            "line": decorator.lineno,
            "decorator": decorator_name,
        }

    def _extract_request_references(self, tree: ast.AST) -> list:
        references = []

        for node in ast.walk(tree):
            if not isinstance(node, ast.Attribute):
                continue

            if (
                isinstance(node.value, ast.Name)
                and node.value.id == "request"
                and node.attr in self.REQUEST_ATTRIBUTES
            ):
                references.append({
                    "reference": f"request.{node.attr}",
                    "line": node.lineno,
                })

        return self._remove_duplicates(references)

    def _extract_database_operations(self, tree: ast.AST) -> list:
        """Extract database operations using basic assignment tracing."""

        operations = []

        database_objects = set()
        cursor_objects = set()

        # First pass: identify database connections and cursor variables.
        for node in ast.walk(tree):

            if isinstance(node, (ast.Assign, ast.AnnAssign)):

                value = node.value

                if not isinstance(value, ast.Call):
                    continue

                # Get assignment target names.
                targets = (
                    node.targets
                    if isinstance(node, ast.Assign)
                    else [node.target]
                )

                target_names = [
                    target.id
                    for target in targets
                    if isinstance(target, ast.Name)
                ]

                called_function = self._get_node_name(value.func)

                # Example: conn = sqlite3.connect(...)
                if called_function.endswith(".connect"):
                    if "sqlite3.connect" in called_function:
                        database_objects.update(target_names)

                # Example: c = conn.cursor()
                elif (
                    called_function.endswith(".cursor")
                    and self._get_call_object(value) in database_objects
                ):
                    cursor_objects.update(target_names)

        # Second pass: classify database-related calls.
        for node in ast.walk(tree):

            if not isinstance(node, ast.Call):
                continue

            if not isinstance(node.func, ast.Attribute):
                continue

            operation = node.func.attr

            if operation not in self.DATABASE_METHODS:
                continue

            object_name = self._get_call_object(node)

            if object_name.startswith("request."):
                classification = "non_database"

            elif (
                operation == "connect"
                and object_name in {"sqlite3", "connectable"}
            ):
                classification = "database_candidate"

            elif (
                object_name in database_objects
                or object_name in cursor_objects
                or object_name in {
                    "conn",
                    "connection",
                    "cursor",
                    "session",
                    "db",
                    "connectable",
                }
            ):
                classification = "database_candidate"

            else:
                classification = "unknown"

            operations.append({
                "operation": operation,
                "object": object_name,
                "line": node.lineno,
                "classification": classification,
            })

        # Remove duplicate records.
        unique_operations = []
        seen = set()

        for item in operations:
            key = (
                item["operation"],
                item["object"],
                item["line"],
            )

            if key not in seen:
                seen.add(key)
                unique_operations.append(item)

        return unique_operations

    def _extract_rendered_templates(self, tree: ast.AST) -> list:
        """Extract templates and context variables passed to render_template()."""

        templates = []

        class FunctionCallVisitor(ast.NodeVisitor):
            def __init__(self):
                self.calls = []

            def visit_FunctionDef(self, node):
                return

            def visit_AsyncFunctionDef(self, node):
                return

            def visit_ClassDef(self, node):
                return

            def visit_Lambda(self, node):
                return

            def visit_Call(self, node):
                self.calls.append(node)
                self.generic_visit(node)

        for node in ast.walk(tree):
            if not isinstance(
                node,
                (ast.FunctionDef, ast.AsyncFunctionDef),
            ):
                continue

            visitor = FunctionCallVisitor()

            for statement in node.body:
                visitor.visit(statement)

            for child in visitor.calls:
                if not isinstance(child.func, ast.Name):
                    continue

                if child.func.id != "render_template":
                    continue

                if not child.args:
                    continue

                template_argument = child.args[0]

                if not (
                    isinstance(template_argument, ast.Constant)
                    and isinstance(template_argument.value, str)
                ):
                    continue

                context_variables = []

                for keyword in child.keywords:
                    # Ignore **kwargs for now because it has no explicit name.
                    if keyword.arg is None:
                        continue

                    context_variables.append({
                        "name": keyword.arg,
                        "source": ast.unparse(keyword.value),
                    })

                templates.append({
                    "function": node.name,
                    "template": template_argument.value,
                    "line": child.lineno,
                    "context_variables": context_variables,
                })

        return self._remove_duplicates_by_template(templates)

    @staticmethod
    def _get_call_object(node: ast.Call) -> str:
        """Extract the object on which a method is called."""

        if isinstance(node.func, ast.Attribute):
            return PythonAnalyzer._get_node_name(node.func.value)

        return ""

    @staticmethod
    def _get_node_name(node: ast.AST) -> str:
        """Convert an AST name or attribute into readable text."""

        if isinstance(node, ast.Name):
            return node.id

        if isinstance(node, ast.Attribute):
            parent = PythonAnalyzer._get_node_name(node.value)
            return f"{parent}.{node.attr}"

        if isinstance(node, ast.Call):
            return PythonAnalyzer._get_node_name(node.func)

        return type(node).__name__

    @staticmethod
    def _remove_duplicates(items: list) -> list:
        unique_items = []
        seen = set()

        for item in items:
            key = (item["reference"], item["line"]) if "reference" in item else (
                item["operation"],
                item["line"],
            )

            if key not in seen:
                seen.add(key)
                unique_items.append(item)

        return unique_items

    @staticmethod
    def _remove_duplicates_by_template(items: list) -> list:
        unique_items = []
        seen = set()

        for item in items:
            key = (
                item["function"],
                item["template"],
                item["line"],
            )

            if key not in seen:
                seen.add(key)
                unique_items.append(item)

        return unique_items