from __future__ import annotations
import hashlib, json
from typing import Any

def sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()

def stable_json_hash(obj: Any) -> str:
    dumped = json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(dumped).hexdigest()
