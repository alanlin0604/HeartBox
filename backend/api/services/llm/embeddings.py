"""BGE-M3 multilingual embeddings via sentence-transformers.

Replaces ``langchain_openai.OpenAIEmbeddings`` (1536-dim) with the
BAAI/bge-m3 model (1024-dim, Apache 2.0). BGE-M3 is the strongest
open-source 繁中 / 英 / 日 embedding model in 2026 and avoids sending
journal-derived content to any external API.

This class subclasses ``langchain_core.embeddings.Embeddings`` so existing
LangChain plumbing (``Chroma.from_documents(embedding=...)``) keeps working
with one line changed at each call site.

Process-isolation note:
  bge-m3 is loaded inside the Django process via sentence-transformers.
  The TAIDE chat model is loaded inside the separate ``llm_server`` FastAPI
  process via bitsandbytes 4-bit. These two stacks are known to have a DLL
  ordering conflict on Windows when imported in the same process, so we
  intentionally split them across processes — never import ``bitsandbytes``
  here.
"""
from __future__ import annotations

import logging
import threading

logger = logging.getLogger(__name__)

DEFAULT_MODEL = 'BAAI/bge-m3'
DEFAULT_DIM = 1024  # bge-m3 dense vector dimension. NB: changing model breaks
                    # the existing Chroma collection — see psychology_kb_bgem3.


try:
    from langchain_core.embeddings import Embeddings as _LCEmbeddings
    _HAS_LANGCHAIN = True
except ImportError:  # pragma: no cover
    _HAS_LANGCHAIN = False

    class _LCEmbeddings:  # type: ignore[no-redef]
        """Minimal stand-in so the class still defines its API when LangChain
        isn't present (e.g. early test-collection time)."""

        def embed_documents(self, texts):  # pragma: no cover
            raise NotImplementedError

        def embed_query(self, text):  # pragma: no cover
            raise NotImplementedError


class BgeM3Embeddings(_LCEmbeddings):
    """LangChain-compatible BGE-M3 embedder.

    Lazy-loads the model on first call so ``manage.py check`` etc. don't pay
    the 2GB model-load cost. The model itself is heavyweight; we hold a single
    module-level instance behind a lock to keep memory usage flat across
    requests.

    Args:
        model_name: HF repo id. Defaults to ``BAAI/bge-m3``.
        device: ``'cpu'`` (default) or ``'cuda'``. CPU is fine — bge-m3 is
            fast enough for the ~30 doc-chunk index size HeartBox has, and
            keeps GPU VRAM free for TAIDE/LLaVA in the separate process.
        normalize: True (default) — bge-m3 produces unit vectors, so cosine
            similarity equals dot product downstream.
    """

    _model_lock = threading.Lock()
    _model = None
    _loaded_name: str | None = None

    def __init__(
        self,
        *,
        model_name: str = DEFAULT_MODEL,
        device: str = 'cpu',
        normalize: bool = True,
        batch_size: int = 16,
    ) -> None:
        self.model_name = model_name
        self.device = device
        self.normalize = normalize
        self.batch_size = batch_size

    # ------------------------------------------------------------------
    # Lazy model load — shared across instances within the same process.
    # ------------------------------------------------------------------
    @classmethod
    def _get_model(cls, model_name: str, device: str):
        if cls._model is not None and cls._loaded_name == model_name:
            return cls._model
        with cls._model_lock:
            if cls._model is not None and cls._loaded_name == model_name:
                return cls._model
            from sentence_transformers import SentenceTransformer
            logger.info('Loading embedding model %s on %s', model_name, device)
            cls._model = SentenceTransformer(model_name, device=device)
            cls._loaded_name = model_name
            return cls._model

    # ------------------------------------------------------------------
    # LangChain Embeddings interface.
    # ------------------------------------------------------------------
    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        model = self._get_model(self.model_name, self.device)
        embeddings = model.encode(
            texts,
            batch_size=self.batch_size,
            normalize_embeddings=self.normalize,
            show_progress_bar=False,
            convert_to_numpy=True,
        )
        return [vec.tolist() for vec in embeddings]

    def embed_query(self, text: str) -> list[float]:
        if not text:
            return [0.0] * DEFAULT_DIM
        model = self._get_model(self.model_name, self.device)
        vec = model.encode(
            text,
            normalize_embeddings=self.normalize,
            show_progress_bar=False,
            convert_to_numpy=True,
        )
        return vec.tolist()


# Convenience for use in non-LangChain contexts (e.g. ad-hoc reindex script).
def encode_one(text: str, model_name: str = DEFAULT_MODEL, device: str = 'cpu') -> list[float]:
    """One-shot embed for a single string."""
    return BgeM3Embeddings(model_name=model_name, device=device).embed_query(text)
