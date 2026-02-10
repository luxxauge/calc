from __future__ import annotations
from pathlib import Path
import shutil

def ensure_dir(p: Path) -> Path:
    p.mkdir(parents=True, exist_ok=True)
    return p

def atomic_write_bytes(dst: Path, data: bytes) -> None:
    ensure_dir(dst.parent)
    tmp = dst.with_suffix(dst.suffix + ".tmp")
    with open(tmp, "wb") as f:
        f.write(data)
    tmp.replace(dst)

def atomic_copy(src: Path, dst: Path) -> None:
    ensure_dir(dst.parent)
    tmp = dst.with_suffix(dst.suffix + ".tmp")
    shutil.copy2(src, tmp)
    tmp.replace(dst)
