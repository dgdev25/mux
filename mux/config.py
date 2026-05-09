from pathlib import Path
import yaml


PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_CONFIG_PATH = PROJECT_ROOT / "config" / "mux.yaml"


def project_root() -> Path:
    return PROJECT_ROOT


def load_config(path: str | None = None) -> dict:
    p = Path(path) if path else DEFAULT_CONFIG_PATH
    return yaml.safe_load(p.read_text())
