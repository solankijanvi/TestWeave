from sentence_transformers import SentenceTransformer
import torch


class EmbeddingModel:
    """
    Generates normalized text embeddings using a Sentence Transformer.

    Uses BGE-small-en-v1.5 as the default embedding model.
    """

    QUERY_INSTRUCTION = (
        "Represent this sentence for searching relevant passages: "
    )

    def __init__(
        self,
        model_name: str = "BAAI/bge-small-en-v1.5",
        device: str = "cpu",
        batch_size: int = 8,
    ) -> None:
        if not isinstance(model_name, str) or not model_name.strip():
            raise ValueError("model_name must be a non-empty string.")

        if (
            not isinstance(batch_size, int)
            or isinstance(batch_size, bool)
            or batch_size <= 0
        ):
            raise ValueError("batch_size must be a positive integer.")

        if not isinstance(device, str) or device not in {"cpu", "cuda", "mps"}:
            raise ValueError("device must be one of: cpu, cuda, mps.")


        self.model_name = model_name
        self.device = device
        self.batch_size = batch_size

        self.model = SentenceTransformer(
            model_name,
            device=device,
        )

    def embed_documents(
        self,
        texts: list[str],
    ) -> torch.Tensor:
        """
        Convert documents into normalized embedding vectors.

        Document text is encoded without a query instruction.
        """

        self._validate_texts(texts)

        embeddings = self.model.encode(
            texts,
            convert_to_tensor=True,
            normalize_embeddings=True,
            batch_size=self.batch_size,
            show_progress_bar=False,
        )

        return embeddings

    def embed_query(
        self,
        query: str,
    ) -> torch.Tensor:
        """
        Convert a search query into a normalized embedding vector.

        Applies the BGE retrieval instruction to the query.
        """

        if not isinstance(query, str) or not query.strip():
            raise ValueError("query must be a non-empty string.")

        instructed_query = self.QUERY_INSTRUCTION + query.strip()

        embedding = self.model.encode(
            instructed_query,
            convert_to_tensor=True,
            normalize_embeddings=True,
            show_progress_bar=False,
        )

        return embedding

    @staticmethod
    def _validate_texts(texts: list[str]) -> None:
        """Validate the document input before encoding."""

        if not isinstance(texts, list) or not texts:
            raise ValueError("texts must be a non-empty list.")

        if any(
            not isinstance(text, str) or not text.strip()
            for text in texts
        ):
            raise ValueError(
                "Every document must be a non-empty string."
            )
