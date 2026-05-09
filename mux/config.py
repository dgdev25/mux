from pathlib import Path
import yaml


def load_config(path: str | None = None) -> dict:
    p = Path(path or "/media/lyle/datadisk/dev/mux/config/mux.yaml")
    return yaml.safe_load(p.read_text())
