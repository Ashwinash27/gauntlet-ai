"""Model manager for downloading and caching ONNX models from HuggingFace Hub.

Models are stored in ~/.gauntlet/models/{model_name}/ and downloaded on first use.
"""

import logging
from pathlib import Path

logger = logging.getLogger(__name__)

_MODELS_DIR = Path.home() / ".gauntlet" / "models"

MODELS = {
    "deberta": {
        "repo_id": "gauntlet-ai/deberta-v3-small-injection",
        "files": [
            "model_quantized.onnx",
            "tokenizer.json",
            "tokenizer_config.json",
            "special_tokens_map.json",
            "config.json",
        ],
    },
    "distilbert": {
        "repo_id": "gauntlet-ai/distilbert-injection",
        "files": [
            "model_quantized.onnx",
            "tokenizer.json",
            "tokenizer_config.json",
            "special_tokens_map.json",
            "vocab.txt",
            "config.json",
        ],
    },
}


def get_model_path(model_name: str) -> Path:
    """Return local path to model directory.

    Args:
        model_name: "deberta" or "distilbert".

    Returns:
        Path to the local model directory.

    Raises:
        ValueError: If model_name is not recognized.
    """
    if model_name not in MODELS:
        raise ValueError(
            f"Unknown model: {model_name}. Available: {', '.join(MODELS.keys())}"
        )
    return _MODELS_DIR / model_name


def is_model_cached(model_name: str) -> bool:
    """Check if a model is already downloaded locally.

    Args:
        model_name: "deberta" or "distilbert".

    Returns:
        True if all model files exist locally.
    """
    model_path = get_model_path(model_name)
    if not model_path.exists():
        return False
    model_info = MODELS[model_name]
    return all((model_path / f).exists() for f in model_info["files"])


def ensure_model(model_name: str) -> Path:
    """Download ONNX model from HF Hub if not cached locally.

    Args:
        model_name: "deberta" or "distilbert".

    Returns:
        Path to the local model directory.

    Raises:
        ValueError: If model_name is not recognized.
        ImportError: If huggingface_hub is not installed.
    """
    if model_name not in MODELS:
        raise ValueError(
            f"Unknown model: {model_name}. Available: {', '.join(MODELS.keys())}"
        )

    model_path = get_model_path(model_name)
    if is_model_cached(model_name):
        logger.debug("Model '%s' already cached at %s", model_name, model_path)
        return model_path

    try:
        from huggingface_hub import hf_hub_download
    except ImportError:
        raise ImportError(
            "Model download requires huggingface-hub. "
            "Install with: pip install gauntlet-ai[slm]"
        )

    model_info = MODELS[model_name]
    repo_id = model_info["repo_id"]
    model_path.mkdir(parents=True, exist_ok=True)

    logger.info("Downloading model '%s' from %s...", model_name, repo_id)
    for filename in model_info["files"]:
        local_file = model_path / filename
        if not local_file.exists():
            downloaded = hf_hub_download(
                repo_id=repo_id,
                filename=filename,
                local_dir=str(model_path),
            )
            logger.debug("Downloaded %s -> %s", filename, downloaded)

    logger.info("Model '%s' ready at %s", model_name, model_path)
    return model_path


__all__ = ["ensure_model", "get_model_path", "is_model_cached", "MODELS"]
