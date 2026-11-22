from __future__ import annotations

import logging
import re
import threading
import time
from types import SimpleNamespace

import pytest

from app.services.content_analysis import model_manager as mm
from app.services.content_analysis.model_manager import (
    ModelFilesMissingError,
    ModelLoadError,
    ModelManager,
    get_model_manager,
)


def test_model_manager_loads_all_models() -> None:
    manager = ModelManager()

    models = manager.models

    assert models.nlp is not None
    assert models.embeddings is not None
    assert models.intent_classifier is not None


def test_model_manager_reuses_loaded_models() -> None:
    manager = ModelManager()

    first = manager.models
    second = manager.models

    assert first is second
    assert first.nlp is second.nlp
    assert first.embeddings is second.embeddings
    assert first.intent_classifier is second.intent_classifier


def test_model_manager_uses_cpu() -> None:
    manager = ModelManager()

    models = manager.models

    assert models.embeddings.device.type == "cpu"

# ---------------------------------------------------------------------------
# Stage 1C: load/unload race, repeated loading and load logging
#
# Everything below uses mocked loaders and a temporary model directory, so
# none of these tests need real NLP models or any network access.
# ---------------------------------------------------------------------------


class _Loaders:
    """Counting fakes for spacy.load, SentenceTransformer and pipeline."""

    def __init__(self) -> None:
        self.spacy_calls = 0
        self.embedding_calls = 0
        self.classifier_calls = 0
        self.fail_spacy_times = 0
        self.entered = threading.Event()
        self.gate: threading.Event | None = None
        self._lock = threading.Lock()

    def spacy_load(self, name, **kwargs):
        with self._lock:
            self.spacy_calls += 1
            should_fail = self.spacy_calls <= self.fail_spacy_times

        self.entered.set()

        if self.gate is not None:
            assert self.gate.wait(timeout=10), "test gate was never released"

        if should_fail:
            raise RuntimeError("boom")

        return SimpleNamespace(max_length=0)

    def sentence_transformer(self, path, **kwargs):
        with self._lock:
            self.embedding_calls += 1

        return SimpleNamespace(device=SimpleNamespace(type=kwargs["device"]))

    def pipeline(self, **kwargs):
        with self._lock:
            self.classifier_calls += 1

        return object()


@pytest.fixture
def loaders(monkeypatch, tmp_path) -> _Loaders:
    (tmp_path / mm.MINILM_MODEL_DIR).mkdir()
    (tmp_path / mm.DEBERTA_MODEL_DIR).mkdir()

    fakes = _Loaders()
    monkeypatch.setattr(
        mm,
        "get_settings",
        lambda: SimpleNamespace(content_analysis_model_dir=tmp_path),
    )
    monkeypatch.setattr(mm.spacy, "load", fakes.spacy_load)
    monkeypatch.setattr(mm, "SentenceTransformer", fakes.sentence_transformer)
    monkeypatch.setattr(mm, "pipeline", fakes.pipeline)

    return fakes


def test_get_model_manager_returns_shared_singleton() -> None:
    assert get_model_manager() is get_model_manager()


def test_repeated_access_loads_each_model_once(loaders: _Loaders) -> None:
    manager = ModelManager()

    bundle = manager.models
    for _ in range(5):
        assert manager.models is bundle
        assert manager.nlp is bundle.nlp
        assert manager.embeddings is bundle.embeddings
        assert manager.intent_classifier is bundle.intent_classifier

    assert loaders.spacy_calls == 1
    assert loaders.embedding_calls == 1
    assert loaders.classifier_calls == 1


def test_loading_is_lazy(loaders: _Loaders) -> None:
    manager = ModelManager()

    assert loaders.spacy_calls == 0

    _ = manager.nlp

    assert loaders.spacy_calls == 1


def test_concurrent_first_access_loads_once(loaders: _Loaders) -> None:
    manager = ModelManager()
    thread_count = 8
    loaders.gate = threading.Event()
    start = threading.Barrier(thread_count)
    results: list[object] = []
    errors: list[BaseException] = []
    results_lock = threading.Lock()

    def worker() -> None:
        try:
            start.wait(timeout=10)
            bundle = manager.models
            with results_lock:
                results.append(bundle)
        except BaseException as exc:  # pragma: no cover - failure path
            with results_lock:
                errors.append(exc)

    threads = [threading.Thread(target=worker) for _ in range(thread_count)]
    for thread in threads:
        thread.start()

    # Hold the first loader inside the load so the others pile up behind
    # the lock. The sleep only makes contention likelier; the assertions
    # below hold whatever the scheduling.
    assert loaders.entered.wait(timeout=10)
    time.sleep(0.05)
    loaders.gate.set()

    for thread in threads:
        thread.join(timeout=10)
        assert not thread.is_alive()

    assert not errors
    assert len(results) == thread_count
    assert all(bundle is results[0] for bundle in results)
    assert loaders.spacy_calls == 1
    assert loaders.embedding_calls == 1
    assert loaders.classifier_calls == 1


class _ReleaseHookLock:
    """Lock that runs a hook immediately after it is released."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self.after_release = None

    def __enter__(self):
        self._lock.acquire()
        return self

    def __exit__(self, *exc_info) -> None:
        self._lock.release()

        hook, self.after_release = self.after_release, None
        if hook is not None:
            hook()


def test_unload_after_lock_release_cannot_invalidate_returned_models(
    loaders: _Loaders,
) -> None:
    manager = ModelManager()
    lock = _ReleaseHookLock()
    manager._lock = lock

    # Simulate unload() winning the lock the instant the loading access
    # releases it, i.e. before that access has returned to its caller.
    lock.after_release = manager.unload

    bundle = manager.models

    assert bundle is not None
    assert bundle.nlp is not None
    assert bundle.embeddings is not None
    assert bundle.intent_classifier is not None
    # The unload really did run afterwards.
    assert manager._models is None


def test_concurrent_unload_during_load_is_serialised(
    loaders: _Loaders,
) -> None:
    manager = ModelManager()
    loaders.gate = threading.Event()
    outcome: dict[str, object] = {}

    def accessor() -> None:
        outcome["bundle"] = manager.models

    def unloader() -> None:
        manager.unload()

    access_thread = threading.Thread(target=accessor)
    access_thread.start()
    assert loaders.entered.wait(timeout=10)

    unload_thread = threading.Thread(target=unloader)
    unload_thread.start()
    time.sleep(0.05)
    loaders.gate.set()

    access_thread.join(timeout=10)
    unload_thread.join(timeout=10)
    assert not access_thread.is_alive()
    assert not unload_thread.is_alive()

    assert outcome["bundle"] is not None
    # unload() ran strictly after the load finished.
    assert manager._models is None


def test_unload_then_access_reloads_models(loaders: _Loaders) -> None:
    manager = ModelManager()

    first = manager.models
    manager.unload()
    second = manager.models

    assert second is not first
    assert loaders.spacy_calls == 2
    assert loaders.embedding_calls == 2
    assert loaders.classifier_calls == 2


def test_load_failure_is_wrapped_and_not_cached(loaders: _Loaders) -> None:
    manager = ModelManager()
    loaders.fail_spacy_times = 1

    with pytest.raises(ModelLoadError) as excinfo:
        _ = manager.models

    assert str(excinfo.value) == "Failed to load Feature 5 local models: boom"
    assert isinstance(excinfo.value.__cause__, RuntimeError)

    # The failure is not cached, so the next access retries and succeeds.
    assert manager.models is not None
    assert loaders.spacy_calls == 2


def test_missing_model_directories_raise_without_loading(
    monkeypatch, tmp_path
) -> None:
    fakes = _Loaders()
    monkeypatch.setattr(
        mm,
        "get_settings",
        lambda: SimpleNamespace(content_analysis_model_dir=tmp_path),
    )
    monkeypatch.setattr(mm.spacy, "load", fakes.spacy_load)

    manager = ModelManager()

    with pytest.raises(ModelFilesMissingError) as excinfo:
        _ = manager.models

    message = str(excinfo.value)
    assert "Required Feature 5 model directories are missing." in message
    assert "scripts/bootstrap_models.py" in message
    assert "MiniLM" in message
    assert "DeBERTa" in message
    assert fakes.spacy_calls == 0


def test_model_errors_share_the_manager_error_base() -> None:
    assert issubclass(ModelFilesMissingError, mm.ModelManagerError)
    assert issubclass(ModelLoadError, mm.ModelManagerError)


def _manager_records(caplog):
    return [r for r in caplog.records if r.name == mm.logger.name]


def test_successful_load_logs_start_and_duration(
    loaders: _Loaders, caplog, tmp_path
) -> None:
    caplog.set_level(logging.INFO, logger=mm.logger.name)

    ModelManager().models

    records = _manager_records(caplog)
    messages = [record.getMessage() for record in records]

    assert messages[0] == "Loading Feature 5 local models."
    assert re.fullmatch(
        r"Feature 5 local models loaded in \d+\.\d{2}s\.", messages[1]
    )
    assert len(records) == 2
    assert all(record.levelno == logging.INFO for record in records)
    # No configuration values (such as the model directory) are logged.
    assert all(str(tmp_path) not in message for message in messages)


def test_cached_access_does_not_log_again(
    loaders: _Loaders, caplog
) -> None:
    manager = ModelManager()
    manager.models

    caplog.clear()
    caplog.set_level(logging.INFO, logger=mm.logger.name)

    manager.models
    manager.nlp

    assert _manager_records(caplog) == []


def test_load_failure_logs_error_with_duration(
    loaders: _Loaders, caplog, tmp_path
) -> None:
    caplog.set_level(logging.INFO, logger=mm.logger.name)
    loaders.fail_spacy_times = 1

    with pytest.raises(ModelLoadError):
        ModelManager().models

    records = _manager_records(caplog)
    assert [r.levelno for r in records] == [logging.INFO, logging.ERROR]

    message = records[1].getMessage()
    assert re.fullmatch(
        r"Feature 5 model loading failed after \d+\.\d{2}s \(ModelLoadError\)\.",
        message,
    )
    assert str(tmp_path) not in message
    # The traceback goes to the server log only; the raised exception and
    # its message are unchanged for the caller.
    assert records[1].exc_info is None
    assert not any("loaded in" in r.getMessage() for r in records)


def test_missing_directories_failure_is_logged(
    monkeypatch, tmp_path, caplog
) -> None:
    monkeypatch.setattr(
        mm,
        "get_settings",
        lambda: SimpleNamespace(content_analysis_model_dir=tmp_path),
    )
    caplog.set_level(logging.INFO, logger=mm.logger.name)

    with pytest.raises(ModelFilesMissingError):
        ModelManager().models

    errors = [
        r for r in _manager_records(caplog) if r.levelno == logging.ERROR
    ]
    assert len(errors) == 1
    assert "ModelFilesMissingError" in errors[0].getMessage()
    assert "failed after" in errors[0].getMessage()