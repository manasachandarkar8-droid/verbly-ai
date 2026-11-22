from __future__ import annotations

from dataclasses import dataclass
import logging
from pathlib import Path
from threading import Lock
import time

import spacy
import torch
from sentence_transformers import SentenceTransformer
from transformers import pipeline

from app.core.config import get_settings


logger = logging.getLogger(__name__)

SPACY_MODEL = "en_core_web_sm"
MINILM_MODEL_DIR = "all-MiniLM-L6-v2"
DEBERTA_MODEL_DIR = "deberta-v3-xsmall-zeroshot"
DEVICE = "cpu"


class ModelManagerError(RuntimeError):
    """Base exception for Feature 5 model-loading failures."""


class ModelFilesMissingError(ModelManagerError):
    """Raised when a required local model is unavailable."""


class ModelLoadError(ModelManagerError):
    """Raised when a local model cannot be loaded."""


@dataclass(frozen=True)
class LoadedModels:
    """Container for the models used by Feature 5."""

    nlp: spacy.language.Language
    embeddings: SentenceTransformer
    intent_classifier: object


class ModelManager:
    """
    Thread-safe, process-local manager for Feature 5 models.

    Models load lazily by default and are reused across requests.
    Runtime model loading must remain local; inference must not
    trigger model downloads.
    """

    def __init__(self) -> None:
        self._models: LoadedModels | None = None
        self._lock = Lock()

    @property
    def models(self) -> LoadedModels:
        """
        Return the loaded model bundle, loading it once if necessary.

        ``self._models`` is read into a local variable exactly once on the
        fast path, and the slow path returns a local reference obtained
        while the lock is held. A concurrent ``unload()`` can therefore
        never turn an access that is already in progress into ``None``.
        """
        models = self._models
        if models is not None:
            return models

        with self._lock:
            models = self._models
            if models is None:
                models = self._load_models()
                self._models = models

            return models

    @property
    def nlp(self) -> spacy.language.Language:
        return self.models.nlp

    @property
    def embeddings(self) -> SentenceTransformer:
        return self.models.embeddings

    @property
    def intent_classifier(self):
        return self.models.intent_classifier

    def _model_directory(self) -> Path:
        """Resolve the configured model directory to an absolute path."""
        settings = get_settings()
        model_dir = Path(settings.content_analysis_model_dir).expanduser()

        if not model_dir.is_absolute():
            model_dir = Path(__file__).resolve().parents[3] / model_dir

        return model_dir.resolve()

    def _load_models(self) -> LoadedModels:
        """Load the model bundle, logging start, duration and failures."""
        started = time.perf_counter()
        logger.info("Loading Feature 5 local models.")

        try:
            models = self._load_local_models()
        except Exception as exc:
            logger.error(
                "Feature 5 model loading failed after %.2fs (%s).",
                time.perf_counter() - started,
                type(exc).__name__,
            )
            raise

        logger.info(
            "Feature 5 local models loaded in %.2fs.",
            time.perf_counter() - started,
        )

        return models

    def _load_local_models(self) -> LoadedModels:
        model_dir = self._model_directory()

        minilm_dir = model_dir / MINILM_MODEL_DIR
        deberta_dir = model_dir / DEBERTA_MODEL_DIR

        self._validate_model_paths(minilm_dir, deberta_dir)

        try:
            nlp = spacy.load(
                SPACY_MODEL,
                disable=["parser", "lemmatizer"],
            )
            nlp.max_length = 51_000

            embeddings = SentenceTransformer(
                str(minilm_dir),
                device=DEVICE,
                local_files_only=True,
            )

            intent_classifier = pipeline(
                task="zero-shot-classification",
                model=str(deberta_dir),
                tokenizer=str(deberta_dir),
                device=-1,
                local_files_only=True,
            )

            return LoadedModels(
                nlp=nlp,
                embeddings=embeddings,
                intent_classifier=intent_classifier,
            )

        except ModelManagerError:
            raise
        except Exception as exc:
            raise ModelLoadError(
                f"Failed to load Feature 5 local models: {exc}"
            ) from exc

    @staticmethod
    def _validate_model_paths(
        minilm_dir: Path,
        deberta_dir: Path,
    ) -> None:
        required_paths = {
            "MiniLM": minilm_dir,
            "DeBERTa": deberta_dir,
        }

        missing = [
            f"{name}: {path}"
            for name, path in required_paths.items()
            if not path.is_dir()
        ]

        if missing:
            details = "; ".join(missing)
            raise ModelFilesMissingError(
                "Required Feature 5 model directories are missing. "
                f"Run scripts/bootstrap_models.py first. Missing: {details}"
            )

    def unload(self) -> None:
        """Release model references for tests or controlled shutdown."""
        with self._lock:
            self._models = None

        if torch.cuda.is_available():
            torch.cuda.empty_cache()


_model_manager = ModelManager()


def get_model_manager() -> ModelManager:
    """Return the shared Feature 5 model manager."""
    return _model_manager