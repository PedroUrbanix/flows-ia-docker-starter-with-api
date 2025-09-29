from __future__ import annotations
from datetime import datetime

def now_iso():
    return datetime.utcnow().replace(microsecond=0).isoformat() + 'Z'

def log(msg: str):
    print(f"[{now_iso()}] {msg}")