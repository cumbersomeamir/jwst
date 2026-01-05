"""Utility functions for JWST pipeline."""

import yaml
from pathlib import Path


def load_config():
    """Load configuration from config.yaml."""
    config_path = Path(__file__).parent.parent / "config.yaml"
    with open(config_path, 'r') as f:
        return yaml.safe_load(f)


def ensure_dir(path):
    """Ensure directory exists, create if needed."""
    path = Path(path)
    if path.suffix:  # It's a file path
        path.parent.mkdir(parents=True, exist_ok=True)
    else:  # It's a directory path
        path.mkdir(parents=True, exist_ok=True)
    return path

