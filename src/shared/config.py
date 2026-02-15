import yaml
import os
from pathlib import Path
from functools import lru_cache

# Path to the root of the project (where config.yaml lives)
BASE_DIR = Path(__file__).resolve().parent.parent.parent
CONFIG_PATH = BASE_DIR / "config.yaml"

class Config:
    def __init__(self, data: dict):
        self.project = data.get("project", {})
        self.server = data.get("server", {})
        self.cors = data.get("cors", {})
        self.database = data.get("database", {})
        self.logging = data.get("logging", {})

@lru_cache()
def load_config() -> Config:
    """Load configuration from YAML file. Cached for performance."""
    if not CONFIG_PATH.exists():
        raise FileNotFoundError(f"Configuration file not found at {CONFIG_PATH}")
    
    with open(CONFIG_PATH, "r") as f:
        data = yaml.safe_load(f)
    
    return Config(data)

config = load_config()
