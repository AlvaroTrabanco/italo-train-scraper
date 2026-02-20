#!/usr/bin/env python3
import argparse
import csv
import json
import os
from typing import Dict, Set, Tuple


HEADER = ["location_name", "lat", "lon"]


def iter_json_files(root: str):
    for dirpath, _, filenames in os.walk(root):
        for fn in filenames:
            if fn.endswith(".json") and fn not in ("_summary.json",):
                yield os.path.join(dirpath, fn)


def load_existing_coords(path: str) -> Dict[str, Tuple[str, str]]:
    """
    Returns mapping: location_name -> (lat, lon) as strings (possibly empty).
    If file doesn't exist, returns empty dict.
    """
    if not os.path.exists(path):
        return {}

    existing: Dict[str, Tuple[str, str]] = {}
    with open(path, "r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        # tolerate slightly different headers if user edited manually
        for row in reader:
            name = (row.get("location_name") or row.get("Location Name") or row.get("name") or "").strip()
            if not name:
                continue
            lat = (row.get("lat") or row.get("Lat") or "").strip()
            lon = (row.get("lon") or row.get("Lon") or row.get("lng") or row.get("Lng") or "").strip()
            existing[name] = (lat, lon)
    return existing


def write_coords(path: str, rows: Dict[str, Tuple[str, str]]) -> None:
    # stable alphabetical output (case-insensitive)
    names = sorted(rows.keys(), key=lambda s: s.casefold())

    with open(path, "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(HEADER)
        for name in names:
            lat, lon = rows[name]
            w.writerow([name, lat, lon])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--input-dir", required=True, help="Folder containing raw Italo JSON runs")
    ap.add_argument("--out", default="coordinates.csv", help="CSV to create/update")
    args = ap.parse_args()

    # 1) load existing coords (preserve edits)
    existing = load_existing_coords(args.out)

    # 2) extract names from JSON
    names: Set[str] = set(existing.keys())

    for path in iter_json_files(args.input_dir):
        try:
            with open(path, "r", encoding="utf-8") as f:
                raw = json.load(f)
        except Exception:
            continue

        ts = (raw or {}).get("TrainSchedule")
        if not ts:
            continue

        def add_name(n):
            if n:
                n = str(n).strip()
                if n:
                    names.add(n)

        # start station
        sp = ts.get("StazionePartenza") or {}
        add_name(sp.get("LocationDescription"))

        # stops
        for k in ("StazioniFerme", "StazioniNonFerme"):
            for s in (ts.get(k) or []):
                add_name((s or {}).get("LocationDescription"))

        # end station description (sometimes not in stop arrays)
        add_name(ts.get("ArrivalStationDescription"))

    # 3) merge: keep existing lat/lon, add blanks for new
    merged: Dict[str, Tuple[str, str]] = {}
    for name in names:
        if name in existing:
            merged[name] = existing[name]
        else:
            merged[name] = ("", "")

    write_coords(args.out, merged)

    added = len(merged) - len(existing)
    print(f"Updated {args.out}: total={len(merged)}, added={added}, preserved={len(existing)}")


if __name__ == "__main__":
    main()