import re
from typing import Any
from collections import Counter
from math import log
import torch
from langchain_core.documents import Document
from nltk.stem import PorterStemmer
from app.rag.embedding_model import EmbeddingModel


class HybridRetriever:
    """
    Retrieves relevant application knowledge using semantic,
    lexical, and exact metadata matching.
    """
    STEMMER = PorterStemmer()
    STOP_WORDS = {
        "a", "an", "and", "are", "does", "for", "from",
        "handles", "how", "in", "is", "of", "on", "or",
        "the", "to", "what", "which", "where", "who",
    }

    def __init__(
        self,
        embedding_model: EmbeddingModel,
    ) -> None:
        if not isinstance(embedding_model, EmbeddingModel):
            raise TypeError(
                "embedding_model must be an EmbeddingModel instance."
            )

        self.embedding_model = embedding_model
        self.documents: list[Document] = []
        self.document_embeddings: torch.Tensor | None = None

    @staticmethod
    def _tokenize(text: str) -> list[str]:
        """Extract and normalize searchable words and identifiers."""

        raw_tokens = re.findall(
            r"[a-zA-Z][a-zA-Z0-9]*",
            text.lower().replace("_", " "),
        )

        return [
            HybridRetriever.STEMMER.stem(token)
            for token in raw_tokens
            if token not in HybridRetriever.STOP_WORDS
        ]
    def index_documents(
        self,
        documents: list[Document],
    ) -> None:
        """Generate and store embeddings for application documents."""

        if not isinstance(documents, list) or not documents:
            raise ValueError(
                "documents must be a non-empty list."
            )

        if any(
            not isinstance(document, Document)
            for document in documents
        ):
            raise TypeError(
                "Every item must be a LangChain Document."
            )

        texts = [
            document.page_content
            for document in documents
        ]

        embeddings = self.embedding_model.embed_documents(texts)

        if embeddings.ndim != 2:
            raise ValueError(
                "Document embeddings must be a 2D tensor."
            )

        if embeddings.shape[0] != len(documents):
            raise ValueError(
                "Number of embeddings must match number of documents."
            )

        self.documents = documents
        self.document_embeddings = embeddings

    def semantic_search(
        self,
        query: str,
        top_k: int = 5,
    ) -> list[tuple[Document, float]]:
        """Retrieve documents using semantic similarity."""

        if not isinstance(query, str) or not query.strip():
            raise ValueError("query must be a non-empty string.")

        if (
            not isinstance(top_k, int)
            or isinstance(top_k, bool)
            or top_k <= 0
        ):
            raise ValueError("top_k must be a positive integer.")

        if self.document_embeddings is None or not self.documents:
            raise RuntimeError(
                "No documents indexed. Call index_documents first."
            )

        query_embedding = self.embedding_model.embed_query(query)

        similarities = torch.matmul(
            self.document_embeddings,
            query_embedding,
        )

        result_count = min(top_k, len(self.documents))

        scores, indices = torch.topk(
            similarities,
            k=result_count,
        )

        results = []

        for score, index in zip(scores, indices):
            document = self.documents[index.item()]
            similarity_score = score.item()
            results.append((document, similarity_score))

        return results

    def metadata_search(
        self,
        filters: dict[str, Any],
        top_k: int = 5,
    ) -> list[Document]:
        """Retrieve documents using exact metadata matching."""

        if not isinstance(filters, dict) or not filters:
            raise ValueError(
                "filters must be a non-empty dictionary."
            )

        if (
            not isinstance(top_k, int)
            or isinstance(top_k, bool)
            or top_k <= 0
        ):
            raise ValueError("top_k must be a positive integer.")

        if not self.documents:
            raise RuntimeError(
                "No documents indexed. Call index_documents first."
            )

        matching_documents = []

        for document in self.documents:
            metadata = document.metadata

            if all(
                metadata.get(key) == value
                for key, value in filters.items()
            ):
                matching_documents.append(document)

        return matching_documents[:top_k]


    def lexical_search(
        self,
        query: str,
        top_k: int = 5,
    ) -> list[tuple[Document, float]]:
        """Retrieve documents using BM25 lexical ranking."""

        if not isinstance(query, str) or not query.strip():
            raise ValueError("query must be a non-empty string.")

        if (
            not isinstance(top_k, int)
            or isinstance(top_k, bool)
            or top_k <= 0
        ):
            raise ValueError("top_k must be a positive integer.")

        if not self.documents:
            raise RuntimeError(
                "No documents indexed. Call index_documents first."
            )

        query_tokens = self._tokenize(query)
        query_terms = set(query_tokens)

        if not query_tokens:
            raise ValueError(
                "Query must contain searchable terms after stop-word removal."
            )

        # BM25 parameters
        k1 = 1.5
        b = 0.5

        # Tokenize every document and calculate document lengths.
        tokenized_documents = []

        for document in self.documents:
            metadata_text = " ".join(
                str(value)
                for value in document.metadata.values()
            )

            searchable_text = (
                document.page_content + " " + metadata_text
            )

            document_tokens = self._tokenize(searchable_text)

            tokenized_documents.append(document_tokens)

        document_count = len(tokenized_documents)

        document_lengths = [
            len(tokens)
            for tokens in tokenized_documents
        ]

        average_document_length = (
            sum(document_lengths) / document_count
        )

        # Calculate how many documents contain each term.
        document_frequencies = Counter()

        for tokens in tokenized_documents:
            document_frequencies.update(set(tokens))

        scored_documents = []

        for document, tokens, document_length in zip(
            self.documents,
            tokenized_documents,
            document_lengths,
        ):
            term_frequencies = Counter(tokens)
            score = 0.0

            for term in sorted(query_terms):
                term_frequency = term_frequencies.get(term, 0)

                if term_frequency == 0:
                    continue

                document_frequency = document_frequencies[term]

                inverse_document_frequency = log(
                    1
                    + (
                        document_count - document_frequency + 0.5
                    )
                    / (
                        document_frequency + 0.5
                    )
                )

                length_normalization = (
                    1 - b
                    + b * document_length / average_document_length
                )

                term_score = (
                    inverse_document_frequency
                    * (
                        term_frequency * (k1 + 1)
                    )
                    / (
                        term_frequency
                        + k1 * length_normalization
                    )
                )

                score += term_score

            if score > 0:
                scored_documents.append((document, score))

        scored_documents.sort(
            key=lambda item: item[1],
            reverse=True,
        )

        return scored_documents[:top_k]

    @staticmethod
    def _get_document_id(document: Document) -> tuple:
        """Generate a stable identifier for a document."""

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

    def reciprocal_rank_fusion(
        self,
        query: str,
        top_k: int = 5,
        rank_constant: int = 60,
    ) -> list[tuple[Document, float]]:
        """Combine semantic and lexical rankings using RRF."""

        if (
            not isinstance(rank_constant, int)
            or isinstance(rank_constant, bool)
            or rank_constant <= 0
        ):
            raise ValueError(
                "rank_constant must be a positive integer."
            )

        candidate_k = max(top_k * 4, top_k)

        semantic_results = self.semantic_search(
            query,
            top_k=candidate_k,
        )

        lexical_results = self.lexical_search(
            query,
            top_k=candidate_k,
        )

        fused_scores = {}
        documents_by_id = {}

        result_lists = [
            semantic_results,
            lexical_results,
        ]

        for results in result_lists:
            for rank, (document, _) in enumerate(
                results,
                start=1,
            ):
                document_id = self._get_document_id(document)

                documents_by_id[document_id] = document

                if document_id not in fused_scores:
                    fused_scores[document_id] = 0.0

                fused_scores[document_id] += (
                    1 / (rank_constant + rank)
                )

        ranked_documents = sorted(
            fused_scores.items(),
            key=lambda item: item[1],
            reverse=True,
        )

        return [
            (documents_by_id[document_id], score)
            for document_id, score in ranked_documents[:top_k]
        ]
