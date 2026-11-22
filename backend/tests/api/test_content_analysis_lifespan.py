from types import SimpleNamespace
from unittest.mock import patch

from fastapi.testclient import TestClient

from app.main import create_app


def make_test_settings(preload: bool) -> SimpleNamespace:
    return SimpleNamespace(
        app_name="Verbly AI Test",
        cors_allow_origins=["*"],
        cors_allow_credentials=True,
        cors_allow_methods=["*"],
        cors_allow_headers=["*"],
        content_analysis_preload_models=preload,
    )


def test_lifespan_does_not_load_local_models_when_preload_enabled():
    test_settings = make_test_settings(True)

    with (
        patch("app.main.settings", test_settings),
        patch(
            "app.services.content_analysis.model_manager.get_model_manager"
        ) as get_model_manager,
    ):
        app = create_app()

        with TestClient(app):
            pass

        get_model_manager.assert_not_called()


def test_lifespan_does_not_load_local_models_when_preload_disabled():
    test_settings = make_test_settings(False)

    with (
        patch("app.main.settings", test_settings),
        patch(
            "app.services.content_analysis.model_manager.get_model_manager"
        ) as get_model_manager,
    ):
        app = create_app()

        with TestClient(app):
            pass

        get_model_manager.assert_not_called()