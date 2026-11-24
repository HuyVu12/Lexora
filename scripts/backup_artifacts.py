#!/usr/bin/env python3
"""Incremental backup of Lexora's git-ignored artifacts that cost money or hours to rebuild.

What is copied (relative to the repository root):
  data/                         pinned source snapshots, normalized bundles, KB and app stores
  experiments/runs/             every run: model extractions, keys, answers, judge grades, retrieval runs
  models/bge-m3-vectors*.sqlite the BGE-M3 vector cache (hours of encoding)
What is skipped because it can be rebuilt quickly: models/bge-m3 (weights, downloadable at the pinned revision) and
models/bge-m3-openvino (converted again from the same weights in about a minute).

A file is copied only when it is new or its size or modification time changed; nothing in the backup is deleted, so
a file removed by mistake in the repository stays in the backup. Each run writes <dest>/manifest.json with size,
mtime and SHA-256 of every file it copied and a summary. SQLite files are copied through SQLite's online backup API,
so a store or cache being written at the same time is copied consistently.

Usage: python scripts/backup_artifacts.py [--dest C:/Users/T14S/Lexora-artifacts] [--dry-run]
Standard library only; offline.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import sqlite3
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCES = [("data", "*"), ("experiments/runs", "*"), ("models", "bge-m3-vectors*.sqlite")]
SQLITE_SUFFIXES = (".sqlite", ".sqlite3", ".db")


def files():
    for folder, pattern in SOURCES:
        base = ROOT / folder
        if not base.exists():
            continue
        if pattern == "*":
            for path in base.rglob("*"):
                if path.is_file() and "__pycache__" not in path.parts and not path.name.endswith((".tmp", "-journal", "-wal", "-shm")):
                    yield path
        else:
            yield from (p for p in base.glob(pattern) if p.is_file())


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def copy(src: Path, dst: Path) -> None:
    dst.parent.mkdir(parents=True, exist_ok=True)
    tmp = dst.with_name(dst.name + ".partial")
    if src.suffix in SQLITE_SUFFIXES:
        source, target = sqlite3.connect(f"file:{src.as_posix()}?mode=ro", uri=True), sqlite3.connect(tmp)
        try:
            source.backup(target)
        finally:
            source.close()
            target.close()
    else:
        shutil.copyfile(src, tmp)
    os.replace(tmp, dst)
    stat = src.stat()
    os.utime(dst, (stat.st_atime, stat.st_mtime))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--dest", default=str(Path.home() / "Lexora-artifacts"), help="backup folder outside the repository")
    parser.add_argument("--dry-run", action="store_true", help="list what would be copied")
    args = parser.parse_args()
    dest = Path(args.dest).resolve()
    if dest == ROOT or ROOT in dest.parents:
        raise SystemExit("the backup folder must be outside the repository")
    manifest_path = dest / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8")) if manifest_path.exists() else {"files": {}, "runs": []}
    copied, skipped, size = [], 0, 0
    started = time.time()
    todo = list(files())
    for number, src in enumerate(todo, 1):
        if number % 50 == 0 or number == len(todo):
            print(f"PROGRESS {number}/{len(todo)} files", file=sys.stderr, flush=True)  # read by Agent Watch from the log
        rel = src.relative_to(ROOT).as_posix()
        stat = src.stat()
        dst = dest / rel
        known = manifest["files"].get(rel)
        if dst.exists() and known and known["size"] == stat.st_size and abs(known["mtime"] - stat.st_mtime) < 1:
            skipped += 1
            continue
        if args.dry_run:
            copied.append(rel)
            size += stat.st_size
            continue
        copy(src, dst)
        manifest["files"][rel] = {"size": stat.st_size, "mtime": stat.st_mtime, "sha256": sha256(dst), "copied": time.time()}
        copied.append(rel)
        size += stat.st_size
    summary = {"at": time.strftime("%Y-%m-%d %H:%M:%S"), "copied": len(copied), "unchanged": skipped,
               "bytes_copied": size, "seconds": round(time.time() - started, 1), "dry_run": args.dry_run}
    if not args.dry_run:
        manifest["runs"].append(summary)
        dest.mkdir(parents=True, exist_ok=True)
        tmp = manifest_path.with_suffix(".tmp")
        tmp.write_text(json.dumps(manifest, ensure_ascii=False, indent=1), encoding="utf-8")
        os.replace(tmp, manifest_path)
    print(json.dumps({"dest": dest.as_posix(), **summary, "examples": copied[:5]}, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    sys.exit(main())
