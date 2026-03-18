#!/usr/bin/env python3
"""Generate a full file tree JSON for os.path.dirname(os.path.abspath(__file__))."""

import os
import json
import time
from pathlib import Path

ROOT = Path("os.path.dirname(os.path.abspath(__file__))")
OUTPUT = ROOT / "data" / "file_tree.json"

SKIP_DIRS = {".git", "__pycache__", ".DS_Store", "node_modules", ".cache"}


def build_tree(path: Path) -> dict:
    stat = path.stat()
    node = {
        "name": path.name,
        "path": str(path),
        "type": "directory" if path.is_dir() else "file",
        "size": stat.st_size,
        "modified": stat.st_mtime,
        "modified_str": time.strftime("%Y-%m-%d %H:%M", time.localtime(stat.st_mtime)),
    }

    if path.is_dir():
        children = []
        try:
            entries = sorted(path.iterdir(), key=lambda p: (p.is_file(), p.name.lower()))
            for entry in entries:
                if entry.name in SKIP_DIRS or entry.name.startswith("."):
                    continue
                children.append(build_tree(entry))
        except PermissionError:
            pass
        node["children"] = children
        node["child_count"] = len(children)
    else:
        node["extension"] = path.suffix.lower()

    return node


def main():
    print(f"Building file tree for {ROOT} ...")
    tree = build_tree(ROOT)

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT, "w") as f:
        json.dump(tree, f, indent=2)

    print(f"Written to {OUTPUT}")
    print("Done.")


if __name__ == "__main__":
    main()
