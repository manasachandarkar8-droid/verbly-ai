from __future__ import annotations

from pathlib import Path

from huggingface_hub import snapshot_download


PROJECT_ROOT = Path(__file__).resolve().parents[1]
MODELS_DIR = PROJECT_ROOT / "models"

MINILM_REPO = "sentence-transformers/all-MiniLM-L6-v2"
MINILM_DIR = MODELS_DIR / "all-MiniLM-L6-v2"

DEBERTA_REPO = "MoritzLaurer/deberta-v3-xsmall-zeroshot-v1.1-all-33"
DEBERTA_DIR = MODELS_DIR / "deberta-v3-xsmall-zeroshot"


def download_model(repo_id: str, local_dir: Path) -> None:
    """Download a Hugging Face model snapshot to a deterministic local directory."""

    local_dir.mkdir(parents=True, exist_ok=True)

    print(f"\nDownloading: {repo_id}")
    print(f"Destination: {local_dir}")

    snapshot_download(
        repo_id=repo_id,
        local_dir=str(local_dir),
    )

    print(f"Completed: {repo_id}")


def main() -> None:
    MODELS_DIR.mkdir(parents=True, exist_ok=True)

    print("Verbly AI — Feature 5 model bootstrap")
    print(f"Models directory: {MODELS_DIR}")

    download_model(
        repo_id=MINILM_REPO,
        local_dir=MINILM_DIR,
    )

    download_model(
        repo_id=DEBERTA_REPO,
        local_dir=DEBERTA_DIR,
    )

    print("\nAll Feature 5 models downloaded successfully.")
    print(f"MiniLM:  {MINILM_DIR}")
    print(f"DeBERTa: {DEBERTA_DIR}")


if __name__ == "__main__":
    main()