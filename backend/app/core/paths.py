from __future__ import annotations

import os
import sys
from pathlib import Path


def is_frozen() -> bool:
    return bool(getattr(sys, "frozen", False))


def get_project_root() -> Path:
    return Path(__file__).resolve().parents[3]


def get_app_data_dir() -> Path:
    override = os.getenv("EASYGET_APP_DATA_DIR")
    if override:
        path = Path(override).expanduser().resolve()
    elif is_frozen():
        local_app_data = Path(os.getenv("LOCALAPPDATA", Path.home() / "AppData" / "Local"))
        path = local_app_data / "Easyget"
    else:
        path = get_project_root()

    path.mkdir(parents=True, exist_ok=True)
    return path


def get_db_path() -> Path:
    override = os.getenv("EASYGET_DB_PATH")
    path = Path(override).expanduser().resolve() if override else get_app_data_dir() / "easyget.db"
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def get_log_path() -> Path:
    override = os.getenv("EASYGET_LOG_PATH")
    path = Path(override).expanduser().resolve() if override else get_app_data_dir() / "backend_debug.log"
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def get_vector_store_path() -> Path:
    override = os.getenv("EASYGET_VECTOR_STORE_PATH")
    if override:
        path = Path(override).expanduser().resolve()
    elif is_frozen():
        path = get_app_data_dir() / "data" / "vector_store.json"
    else:
        path = get_project_root() / "backend" / "data" / "vector_store.json"

    path.parent.mkdir(parents=True, exist_ok=True)
    return path
