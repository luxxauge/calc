from __future__ import annotations
from pathlib import Path

APP_NAME = "ElektroCalc"
DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8765

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)

DB_PATH = DATA_DIR / "electrocalc.db"
DB_URL = f"sqlite:///{DB_PATH.as_posix()}"

ASSETS_ROOT = DATA_DIR / "projects"
ASSETS_ROOT.mkdir(parents=True, exist_ok=True)


IMPORTS_DIR = DATA_DIR / "imports"
IMPORTS_DIR.mkdir(parents=True, exist_ok=True)
