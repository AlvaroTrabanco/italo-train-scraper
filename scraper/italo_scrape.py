#!/usr/bin/env python3
import argparse
import json
import os
import time
from datetime import datetime, timezone
from typing import Dict, Any, Optional, Tuple, List

import requests

API_TEMPLATE = "https://italoinviaggio.italotreno.com/api/RicercaTrenoService?&TrainNumber={train}"


def fetch_json(session: requests.Session, train: str, timeout: int, retries: int) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
    url = API_TEMPLATE.format(train=train)
    last_err: Optional[str] = None
    for attempt in range(retries + 1):
        try:
            r = session.get(url, timeout=timeout, headers={"User-Agent": "Mozilla/5.0"})
            if r.status_code != 200:
                last_err = f"HTTP {r.status_code}"
                time.sleep(0.4 + 0.5 * attempt)
                continue
            return r.json(), None
        except Exception as e:
            last_err = str(e)
            time.sleep(0.4 + 0.5 * attempt)
    return None, last_err


def ensure_dir(p: str) -> None:
    os.makedirs(p, exist_ok=True)


def write_json(path: str, payload: Dict[str, Any]) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)


def build_slice(range_start: int, range_end: int, slice_size: int, slice_index: int) -> List[int]:
    """
    Split [range_start, range_end] into consecutive slices of length slice_size.
    slice_index selects which slice to run.
    """
    if range_end < range_start:
        raise ValueError("range_end must be >= range_start")
    if slice_size <= 0:
        raise ValueError("slice_size must be > 0")

    total = range_end - range_start + 1
    num_slices = (total + slice_size - 1) // slice_size
    idx = slice_index % num_slices  # wrap around safely

    start = range_start + idx * slice_size
    end = min(range_end, start + slice_size - 1)
    return list(range(start, end + 1))


def main() -> None:
    ap = argparse.ArgumentParser(description="Hourly slicer scraper for Italo 'italoinviaggio' by train number.")
    ap.add_argument("--range-start", type=int, default=0)
    ap.add_argument("--range-end", type=int, default=9999)
    ap.add_argument("--slice-size", type=int, default=500, help="How many train numbers per run.")
    ap.add_argument("--slice-index", type=int, required=True, help="Which slice to run (will wrap automatically).")

    ap.add_argument("--outdir", default="out")
    ap.add_argument("--timeout", type=int, default=25)
    ap.add_argument("--retries", type=int, default=2)
    ap.add_argument("--skip-empty", action="store_true")
    ap.add_argument("--sleep", type=float, default=0.15, help="Base delay between requests.")
    ap.add_argument("--jitter", type=float, default=0.15, help="Random extra delay per request.")
    args = ap.parse_args()

    run_ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    run_dir = os.path.join(args.outdir, run_ts)
    ensure_dir(run_dir)

    trains = build_slice(args.range_start, args.range_end, args.slice_size, args.slice_index)

    session = requests.Session()
    stats = {"ok": 0, "empty": 0, "error": 0}

    import random
    for n in trains:
        train = str(n)
        payload, err = fetch_json(session, train, timeout=args.timeout, retries=args.retries)

        if payload is None:
            stats["error"] += 1
            write_json(os.path.join(run_dir, f"{train}.error.json"), {"train": train, "error": err})
        else:
            is_empty = bool(payload.get("IsEmpty", False))
            if is_empty:
                stats["empty"] += 1
                if not args.skip_empty:
                    write_json(os.path.join(run_dir, f"{train}.json"), payload)
            else:
                stats["ok"] += 1
                write_json(os.path.join(run_dir, f"{train}.json"), payload)

        time.sleep(args.sleep + random.random() * args.jitter)

    write_json(os.path.join(run_dir, "_summary.json"), {
        "run_utc": run_ts,
        "range": [args.range_start, args.range_end],
        "slice_size": args.slice_size,
        "slice_index": args.slice_index,
        "counts": stats,
        "total_trains_this_run": len(trains),
    })

    print(f"Done {run_ts}: OK={stats['ok']} EMPTY={stats['empty']} ERROR={stats['error']} (checked={len(trains)})")


if __name__ == "__main__":
    main()