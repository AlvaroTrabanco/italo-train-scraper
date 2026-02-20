#!/usr/bin/env python3
import argparse
import json
import os
import time
from datetime import datetime, timezone
from typing import Dict, Any, Optional, Tuple, List

import requests

API_TEMPLATE = "https://italoinviaggio.italotreno.com/api/RicercaTrenoService?&TrainNumber={train}"


def read_trains(path: str) -> List[str]:
    trains: List[str] = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            t = line.strip()
            if not t or t.startswith("#"):
                continue
            trains.append(t)
    return trains


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


def slice_list(items: List[str], slice_size: int, slice_index: int) -> List[str]:
    if slice_size <= 0:
        raise ValueError("slice_size must be > 0")
    if not items:
        return []
    num_slices = (len(items) + slice_size - 1) // slice_size
    idx = slice_index % num_slices
    start = idx * slice_size
    end = min(len(items), start + slice_size)
    return items[start:end]


def main() -> None:
    ap = argparse.ArgumentParser(description="Scrape Italo italoinviaggio by train number from trains.txt.")
    ap.add_argument("--trains-file", default="scraper/trains.txt")
    ap.add_argument("--slice-size", type=int, default=200, help="How many train numbers per run.")
    ap.add_argument("--slice-index", type=int, default=0, help="Which slice to run (wraps automatically).")
    ap.add_argument("--outdir", default="out")
    ap.add_argument("--timeout", type=int, default=25)
    ap.add_argument("--retries", type=int, default=2)
    ap.add_argument("--skip-empty", action="store_true")
    ap.add_argument("--sleep", type=float, default=0.15)
    ap.add_argument("--jitter", type=float, default=0.20)
    args = ap.parse_args()

    trains_all = read_trains(args.trains_file)
    if not trains_all:
        raise SystemExit(f"No trains found in {args.trains_file}")

    trains = slice_list(trains_all, args.slice_size, args.slice_index)

    run_ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    run_dir = os.path.join(args.outdir, run_ts)
    ensure_dir(run_dir)

    session = requests.Session()
    stats = {"ok": 0, "empty": 0, "error": 0}

    import random
    for train in trains:
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
        "slice_size": args.slice_size,
        "slice_index": args.slice_index,
        "total_trains_in_file": len(trains_all),
        "total_trains_this_run": len(trains),
        "slice_first": trains[0] if trains else None,
        "slice_last": trains[-1] if trains else None,
        "counts": stats,
    })

    print(f"Done {run_ts}: OK={stats['ok']} EMPTY={stats['empty']} ERROR={stats['error']} checked={len(trains)}")


if __name__ == "__main__":
    main()