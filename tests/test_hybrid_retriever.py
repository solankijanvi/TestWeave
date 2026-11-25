import unittest
from pathlib import Path

from app.rag.document_processor import DocumentProcessor
from app.rag.embedding_model import EmbeddingModel
from app.rag.hybrid_retriever import HybridRetriever


class TestHybridRetriever(unittest.TestCase):

    def test_prediction_function_ranks_second(self):
        knowledge_path = (
            Path(__file__).resolve().parent
            / "fixtures"
            / "application_knowledge.json"
        )

        processor = DocumentProcessor()
        knowledge = processor.load_knowledge(str(knowledge_path))
        documents = processor.create_documents(knowledge)

        # Lexical retrieval does not require model initialization.
        embedding_model = object.__new__(EmbeddingModel)
        retriever = HybridRetriever(embedding_model)

        retriever.documents = documents

        results = retriever.lexical_search(
            "Which backend function processes cattle disease predictions?",
            top_k=2,
        )

        ranked_ids = [
            retriever._get_document_id(document)
            for document, score in results
        ]

        expected_route_id = ("routes", 2)
        expected_function_id = ("functions", 2)

        self.assertEqual(
            ranked_ids[0],
            expected_route_id,
            msg="The /predict route should rank first.",
        )

        self.assertEqual(
            ranked_ids.index(expected_function_id) + 1,
            2,
            msg=(
                "The backend prediction function should rank "
                "second for the cattle disease prediction query."
            ),
        )


if __name__ == "__main__":
    unittest.main()
