import json
from pathlib import Path

from app.codebase.python_analyzer import PythonAnalyzer
from app.codebase.template_analyzer import TemplateAnalyzer
from app.codebase.javascript_analyzer import JavaScriptAnalyzer
from app.codebase.application_mapper import ApplicationMapper
from app.codebase.data_flow_mapper import DataFlowMapper
from app.knowledge.knowledge_builder import KnowledgeBuilder
from app.knowledge.knowledge_exporter import KnowledgeExporter


ROOT = Path(__file__).resolve().parent
SOURCE = ROOT / "tests" / "fixtures" / "application_knowledge.json"
OUTPUT = ROOT / "tests" / "fixtures" / "application_knowledge.refreshed.json"


def main():
    with SOURCE.open("r", encoding="utf-8") as file:
        old_knowledge = json.load(file)

    metadata = old_knowledge["application"]
    old_repository = old_knowledge["repository"]

    repository_data = {
        "repository": {
            "full_name": metadata["name"],
            "description": metadata["description"],
            "default_branch": metadata["default_branch"],
        },
        "total_files_discovered": old_repository["total_files_discovered"],
        "eligible_files_count": old_repository["eligible_files_count"],
        "downloaded_files_count": old_repository["downloaded_files_count"],
        "failed_files_count": old_repository["failed_files_count"],
        "files": old_knowledge["files"],
        "failed_files": [],
    }

    python_result = PythonAnalyzer().analyze_repository(repository_data)
    template_result = TemplateAnalyzer().analyze_repository(repository_data)
    javascript_result = JavaScriptAnalyzer().analyze_repository(repository_data)

    mapping_result = ApplicationMapper().map_application(
        python_result,
        template_result,
        javascript_result,
    )

    data_flow_result = DataFlowMapper().map_data_flow(
        python_result,
        template_result,
    )

    knowledge = KnowledgeBuilder().build(
        repository_data=repository_data,
        python_result=python_result,
        template_result=template_result,
        mapping_result=mapping_result,
        data_flow_result=data_flow_result,
    )

    KnowledgeExporter().export(
        knowledge=knowledge,
        output_path=str(OUTPUT),
    )

    print(f"Refreshed fixture written to: {OUTPUT}")
    print(f"Files analyzed: {len(repository_data['files'])}")
    print(f"JavaScript files analyzed: {javascript_result['total_javascript_files']}")
    print(f"Forms mapped: {len(knowledge['form_route_mappings'])}")
    print("Form mapping statuses:")

    for mapping in knowledge["form_route_mappings"]:
        print(
            f"  {mapping.get('form_id')}: "
            f"{mapping.get('mapping_status')} "
            f"(endpoint={mapping.get('endpoint')})"
        )

    print("Mapping status counts:")
    print(knowledge["statistics"]["form_mapping_status_counts"])


if __name__ == "__main__":
    main()
