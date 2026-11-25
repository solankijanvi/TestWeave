from app.rag.document_processor import DocumentProcessor
from app.rag.embedding_model import EmbeddingModel
from app.rag.hybrid_retriever import HybridRetriever
from pathlib import Path
KNOWLEDGE_PATH = (
    Path(__file__).resolve().parent
    / "fixtures"
    / "application_knowledge.json"
)
TOP_K = 5

# Each record is identified by its knowledge collection and record index.

EVALUATION_DATASET = [
    {
        "query": "Which route handles GET requests for the home page?",
        "relevant_documents": {
            ("routes", 0),
        },
    },
    {
        "query": "Which route handles POST requests for the contact form?",
        "relevant_documents": {
            ("routes", 4),
            ("form_route_mappings", 0),
        },
    },
    {
        "query": "Which route supports both GET and POST for cattle disease prediction?",
        "relevant_documents": {
            ("routes", 2),
        },
    },
    {
        "query": "Which route displays customer reviews?",
        "relevant_documents": {
            ("routes", 3),
            ("rendered_templates", 4),
        },
    },
    {
        "query": "Which function creates the SQLite database?",
        "relevant_documents": {
            ("functions", 5),
        },
    },
    {
        "query": "Which function imports CSV data into the database?",
        "relevant_documents": {
            ("functions", 6),
        },
    },
    {
        "query": "Which backend function processes cattle disease predictions?",
        "relevant_documents": {
            ("functions", 2),
        },
    },
    {
        "query": "Which fields are required in the contact form?",
        "relevant_documents": {
            ("forms", 0),
            ("form_route_mappings", 0),
        },
    },
    {
        "query": "Which fields are present in the cattle disease prediction form?",
        "relevant_documents": {
            ("forms", 1),
            ("form_route_mappings", 1),
        },
    },
    {
        "query": "Which template contains the review submission form?",
        "relevant_documents": {
            ("forms", 2),
            ("form_route_mappings", 2),
        },
    },
    {
        "query": "Which backend endpoint receives the contact form submission?",
        "relevant_documents": {
            ("form_route_mappings", 0),
            ("routes", 4),
        },
    },
    {
        "query": "Why is the review form classified as client-side?",
        "relevant_documents": {
            ("form_route_mappings", 2),
        },
    },
    {
        "query": "Which backend variable supplies symptoms to the frontend loop?",
        "relevant_documents": {
            ("data_flows", 0),
        },
    },
    {
        "query": "How does the prediction variable appear in the frontend template?",
        "relevant_documents": {
            ("data_flows", 1),
        },
    },
    {
        "query": "Where does the application establish a SQLite database connection?",
        "relevant_documents": {
            ("database_operations", 9),
            ("database_operations", 14),
        },
    },
    {
        "query": "Which database operation commits changes to the SQLite database?",
        "relevant_documents": {
            ("database_operations", 11),
        },
    },
    {
        "query": "Which template is rendered by the prediction function with prediction and symptoms data?",
        "relevant_documents": {
            ("rendered_templates", 3),
        },
    },
]


def get_document_id(document):
    """Return a stable, unique identifier for a document."""

    metadata = document.metadata

    if metadata.get("source_type") == "files":
        return (
            metadata.get("source_type"),
            metadata.get("path"),
            metadata.get("chunk_index"),
        )

    return (
        metadata.get("source_type"),
        metadata.get("record_index"),
    )


def _validate_k(k):
    """Ensure k is a positive integer."""
    if isinstance(k, bool) or not isinstance(k, int) or k <= 0:
        raise ValueError("k must be a positive integer.")


def precision_at_k(retrieved_ids, relevant_ids, k):
    """Calculate precision among unique retrieved top-k documents."""

    _validate_k(k)

    top_results = list(dict.fromkeys(retrieved_ids[:k]))

    if not top_results:
        return 0.0

    return (
        len(set(top_results) & relevant_ids)
        / len(top_results)
    )

def recall_at_k(retrieved_ids, relevant_ids, k):
    """Calculate the fraction of relevant documents retrieved in top-k."""

    _validate_k(k)

    if not relevant_ids:
        raise ValueError("relevant_ids must not be empty.")

    top_results = retrieved_ids[:k]

    return (
        len(set(top_results) & relevant_ids)
        / len(relevant_ids)
    )


def reciprocal_rank(retrieved_ids, relevant_ids):
    """Calculate the reciprocal rank of the first relevant result."""

    for rank, document_id in enumerate(retrieved_ids, start=1):
        if document_id in relevant_ids:
            return 1 / rank

    return 0.0

def evaluate_retriever(retriever, method_name):
    """Evaluate a retrieval method using the labeled query dataset."""

    if method_name == "lexical_search":
        search_method = retriever.lexical_search
    elif method_name == "semantic_search":
        search_method = retriever.semantic_search
    elif method_name == "reciprocal_rank_fusion":
        search_method = retriever.reciprocal_rank_fusion
    else:
        raise ValueError(
            f"Unsupported retrieval method: {method_name}"
        )

    precision_scores = []
    recall_scores = []
    reciprocal_rank_scores = []

    print(f"\n\n{'#' * 65}")
    print(f"RETRIEVAL METHOD: {method_name.upper()}")
    print(f"{'#' * 65}")

    for item in EVALUATION_DATASET:
        query = item["query"]
        relevant_ids = item["relevant_documents"]

        results = search_method(query, top_k=TOP_K)

        retrieved_ids = [
            get_document_id(document)
            for document, score in results
        ]

        precision = precision_at_k(
            retrieved_ids, relevant_ids, TOP_K
        )

        recall = recall_at_k(
            retrieved_ids, relevant_ids, TOP_K
        )

        mrr = reciprocal_rank(
            retrieved_ids, relevant_ids
        )

        precision_scores.append(precision)
        recall_scores.append(recall)
        reciprocal_rank_scores.append(mrr)

        print(f"\nQUERY: {query}")
        print("-" * 65)

        for rank, (document, score) in enumerate(results, start=1):
            document_id = get_document_id(document)

            print(
                f"Rank: {rank} | "
                f"Score: {score:.4f} | "
                f"ID: {document_id} | "
                f"Relevant: {document_id in relevant_ids}"
            )

        print(f"\nPrecision@{TOP_K}: {precision:.4f}")
        print(f"Recall@{TOP_K}:    {recall:.4f}")
        print(f"Reciprocal Rank:   {mrr:.4f}")

    print(f"\n{'=' * 65}")
    print(f"{method_name.upper()} — OVERALL METRICS")
    print(f"{'=' * 65}")

    print(
        f"Mean Precision@{TOP_K}: "
        f"{sum(precision_scores) / len(precision_scores):.4f}"
    )

    print(
        f"Mean Recall@{TOP_K}: "
        f"{sum(recall_scores) / len(recall_scores):.4f}"
    )

    print(
        f"Mean Reciprocal Rank: "
        f"{sum(reciprocal_rank_scores) / len(reciprocal_rank_scores):.4f}"
    )



def main():
    processor = DocumentProcessor()

    knowledge = processor.load_knowledge(KNOWLEDGE_PATH)

    documents = processor.create_documents(knowledge)
    documents = processor.split_documents(documents)

    embedding_model = EmbeddingModel(device="cpu")

    retriever = HybridRetriever(embedding_model)
    retriever.index_documents(documents)

    evaluate_retriever(retriever, "lexical_search")
    evaluate_retriever(retriever, "semantic_search")
    evaluate_retriever(retriever, "reciprocal_rank_fusion")


if __name__ == "__main__":
    main()
