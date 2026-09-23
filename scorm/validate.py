import os, re
from typing import Dict

SAFE_NAME = re.compile(r"[^a-zA-Z0-9._-]+")

def safe_filename(name: str) -> str:
    name = os.path.basename(name)
    name = SAFE_NAME.sub("_", name).strip("._")
    return (name or "file")[:120]

def safe_relpath(path: str) -> str:
    path = path.replace("\\", "/").strip().lstrip("/")
    if ".." in path.split("/"):
        raise ValueError("Invalid path traversal")
    return path

def validate_assets_map(assets: Dict[str, bytes]) -> Dict[str, bytes]:
    cleaned = {}
    for k, v in assets.items():
        kp = safe_relpath(k)
        folder, filename = os.path.split(kp)
        filename = safe_filename(filename)
        kp2 = f"{folder}/{filename}" if folder else filename
        cleaned[kp2] = v
    return cleaned
