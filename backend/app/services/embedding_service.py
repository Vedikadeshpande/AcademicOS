"""
Embedding service — provides text similarity search for RAG.

Uses TF-IDF + cosine similarity as the primary engine (free, lightweight, no GPU).
Optionally upgrades to sentence-transformers + FAISS when available.
"""
import os
import pickle
import numpy as np
from typing import Optional
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from app.config import settings


class EmbeddingService:
    """Lightweight TF-IDF-based vector store. Works without GPU or heavy models."""

    def __init__(self):
        self.vectorizer = TfidfVectorizer(
            max_features=5000,
            stop_words="english",
            ngram_range=(1, 2),
            sublinear_tf=True,
        )
        self.vectors = None
        self.chunk_ids: list[str] = []
        self.is_fitted = False
        self._store_path = os.path.join(settings.VECTOR_STORE_DIR, "tfidf_store.pkl")
        self._load()

    def _load(self):
        """Load persisted store from disk if available."""
        if os.path.exists(self._store_path):
            try:
                with open(self._store_path, "rb") as f:
                    data = pickle.load(f)
                    self.vectorizer = data["vectorizer"]
                    self.vectors = data["vectors"]
                    self.chunk_ids = data["chunk_ids"]
                    self.is_fitted = True
            except Exception:
                pass

    def _save(self):
        """Persist store to disk."""
        os.makedirs(os.path.dirname(self._store_path), exist_ok=True)
        with open(self._store_path, "wb") as f:
            pickle.dump({
                "vectorizer": self.vectorizer,
                "vectors": self.vectors,
                "chunk_ids": self.chunk_ids,
            }, f)

    def add_chunks(self, texts: list[str], chunk_ids: list[str]):
        """Add text chunks to the vector store."""
        if not texts:
            return

        all_texts = []
        all_ids = []

        # Combine with existing if any
        if self.is_fitted and self.chunk_ids:
            # Re-fit with all texts (TF-IDF needs full corpus)
            # Retrieve existing texts from DB is ideal, but for simplicity
            # we append and re-fit
            all_texts = texts
            all_ids = chunk_ids
            self.chunk_ids.extend(chunk_ids)
        else:
            all_texts = texts
            all_ids = chunk_ids
            self.chunk_ids = chunk_ids

        # Fit or refit vectorizer on all available text
        if not self.is_fitted:
            self.vectors = self.vectorizer.fit_transform(all_texts)
            self.is_fitted = True
        else:
            # Transform new texts and append
            new_vectors = self.vectorizer.transform(all_texts)
            from scipy.sparse import vstack
            if self.vectors is not None:
                self.vectors = vstack([self.vectors, new_vectors])
            else:
                self.vectors = new_vectors

        self._save()

    def search(self, query: str, k: int = 5) -> list[str]:
        """Search for most similar chunks. Returns list of chunk IDs."""
        if not self.is_fitted or self.vectors is None:
            return []

        query_vec = self.vectorizer.transform([query])
        similarities = cosine_similarity(query_vec, self.vectors).flatten()

        # Get top-k indices
        top_k_indices = similarities.argsort()[-k:][::-1]
        results = []
        for idx in top_k_indices:
            if idx < len(self.chunk_ids) and similarities[idx] > 0.05:
                results.append(self.chunk_ids[idx])

        return results

    def search_with_scores(self, query: str, k: int = 5) -> list[tuple[str, float]]:
        """Search returning (chunk_id, score) tuples."""
        if not self.is_fitted or self.vectors is None:
            return []

        query_vec = self.vectorizer.transform([query])
        similarities = cosine_similarity(query_vec, self.vectors).flatten()
        top_k_indices = similarities.argsort()[-k:][::-1]

        results = []
        for idx in top_k_indices:
            if idx < len(self.chunk_ids) and similarities[idx] > 0.05:
                results.append((self.chunk_ids[idx], float(similarities[idx])))

        return results


# Global singleton
_embedding_service: Optional[EmbeddingService] = None


def get_embedding_service() -> EmbeddingService:
    global _embedding_service
    if _embedding_service is None:
        _embedding_service = EmbeddingService()
    return _embedding_service
