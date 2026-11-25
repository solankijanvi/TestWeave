
import json
from pathlib import Path


class KnowledgeExporter:
    """
    Exports unified application knowledge
    into a JSON file.
    """

    def export(
        self,
        knowledge: dict,
        output_path: str,
    ) -> None:
        """
        Save application knowledge as JSON.
        """

        output_file = Path(output_path)

        output_file.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        with output_file.open(
            "w",
            encoding="utf-8",
        ) as file:
            json.dump(
                knowledge,
                file,
                indent=4,
                ensure_ascii=False,
            )

        print(f"Knowledge exported to: {output_file}")
