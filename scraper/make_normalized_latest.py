#!/usr/bin/env python3
import argparse
import os
import shutil
from pathlib import Path

def main() -> None:
    ap = argparse.ArgumentParser(description="Merge normalized/<RUN_UTC>/*.normalized.json into normalized_latest/")
    ap.add_argument("--normalized-root", default="normalized", help="Root folder containing run dirs (default: normalized)")
    ap.add_argument("--out-dir", default="normalized_latest", help="Output folder (default: normalized_latest)")
    args = ap.parse_args()

    normalized_root = Path(args.normalized_root)
    out_dir = Path(args.out_dir)

    if not normalized_root.exists() or not normalized_root.is_dir():
        raise SystemExit(f"Missing or invalid --normalized-root: {normalized_root}")

    out_dir.mkdir(parents=True, exist_ok=True)

    run_dirs = sorted([p for p in normalized_root.iterdir() if p.is_dir()])
    if not run_dirs:
        raise SystemExit(f"No run directories found under {normalized_root}")

    copied = 0
    for run in run_dirs:
        files = list(run.glob("*.normalized.json"))
        for src in files:
            dst = out_dir / src.name
            shutil.copy2(src, dst)  # overwrite if exists
            copied += 1

    # Count unique trains in output
    unique = len(list(out_dir.glob("*.normalized.json")))
    print(f"Merged {len(run_dirs)} runs; copied {copied} files; normalized_latest now has {unique} files")

if __name__ == "__main__":
    main()