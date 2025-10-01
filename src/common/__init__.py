from __future__ import annotations

from pathlib import Path

try:
    from dotenv import load_dotenv
except ImportError:  # pragma: no cover - optional dependency
    load_dotenv = None

if load_dotenv is not None:
    project_root = Path(__file__).resolve().parents[2]
    load_dotenv(project_root / ".env", override=False)
