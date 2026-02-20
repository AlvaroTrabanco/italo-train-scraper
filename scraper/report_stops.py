#!/usr/bin/env python3
import argparse
import csv
import json
import os
from typing import Dict, Any, Set, Tuple, List


def load_coords_csv(path: str) -> Dict[str, Tuple[str, str]]:
    coords: Dict[str, Tuple[str, str]] = {}
    if not os.path.exists(path):
        return coords
    with open(path, "r", encoding="utf-8", newline="") as f:
        r = csv.DictReader(f)
        for row in r:
            name = (row.get("location_name") or "").strip()
            if not name:
                continue
            lat = (row.get("lat") or "").strip()
            lon = (row.get("lon") or "").strip()
            coords[name] = (lat, lon)
    return coords


def iter_normalized_files(norm_dir: str):
    for fn in os.listdir(norm_dir):
        if fn.endswith(".normalized.json"):
            yield os.path.join(norm_dir, fn)


def load_json(path: str) -> Dict[str, Any]:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def write_text(path: str, s: str) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(s)


def write_csv(path: str, header: List[str], rows: List[List[str]]) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(header)
        w.writerows(rows)


def has_valid_coord(lat: str, lon: str) -> bool:
    try:
        if lat == "" or lon == "":
            return False
        la = float(lat)
        lo = float(lon)
        return -90 <= la <= 90 and -180 <= lo <= 180
    except Exception:
        return False


def main() -> None:
    ap = argparse.ArgumentParser(description="Report coordinate coverage for stops seen in a normalized run.")
    ap.add_argument("--normalized-dir", required=True, help="normalized/<run_utc> directory")
    ap.add_argument("--coordinates", default="coordinates.csv", help="coordinates.csv path")
    ap.add_argument("--out-dir", required=True, help="Output folder for report (e.g. public/reports)")
    ap.add_argument("--run-utc", required=True, help="Run identifier (folder name)")
    args = ap.parse_args()

    coords = load_coords_csv(args.coordinates)

    observed: Set[str] = set()
    trains_ok = 0

    for path in iter_normalized_files(args.normalized_dir):
        trains_ok += 1
        data = load_json(path)
        for s in data.get("stops", []):
            name = (s.get("stop_name") or "").strip()
            if name:
                observed.add(name)

    ok: List[str] = []
    missing: List[str] = []
    new_not_in_coords: List[str] = []
    unused_in_coords: List[str] = []

    for name in sorted(observed, key=lambda x: x.casefold()):
        if name not in coords:
            new_not_in_coords.append(name)
        else:
            lat, lon = coords[name]
            if has_valid_coord(lat, lon):
                ok.append(name)
            else:
                missing.append(name)

    for name in sorted(set(coords.keys()) - observed, key=lambda x: x.casefold()):
        unused_in_coords.append(name)

    rows = []
    for name in sorted(observed, key=lambda x: x.casefold()):
        if name not in coords:
            status = "NEW_NOT_IN_COORDINATES"
            lat = lon = ""
        else:
            lat, lon = coords[name]
            status = "HAS_COORDINATES" if has_valid_coord(lat, lon) else "MISSING_COORDINATES"
        rows.append([name, status, lat, lon])

    os.makedirs(args.out_dir, exist_ok=True)
    dated_csv = os.path.join(args.out_dir, f"stops_report_{args.run_utc}.csv")
    dated_md = os.path.join(args.out_dir, f"stops_report_{args.run_utc}.md")

    write_csv(dated_csv, ["location_name", "status", "lat", "lon"], rows)

    md = []
    md.append("# Italo stops coordinates report\n\n")
    md.append(f"- Run: `{args.run_utc}`\n")
    md.append(f"- Normalized trains (ok): **{trains_ok}**\n")
    md.append(f"- Unique stops observed: **{len(observed)}**\n")
    md.append(f"- Stops with coordinates: **{len(ok)}**\n")
    md.append(f"- Stops missing coordinates: **{len(missing)}**\n")
    md.append(f"- New stops not in coordinates.csv: **{len(new_not_in_coords)}**\n")
    md.append(f"- Coordinates entries unused this run: **{len(unused_in_coords)}**\n")

    def section(title: str, items: List[str], limit: int = 200):
        md.append(f"\n## {title} ({len(items)})\n")
        if not items:
            md.append("_None_\n")
            return
        if len(items) > limit:
            md.append(f"_Showing first {limit} only. See CSV for full list._\n")
            items = items[:limit]
        for x in items:
            md.append(f"- {x}\n")

    section("Missing coordinates", missing)
    section("New stops not in coordinates.csv", new_not_in_coords)
    section("Has coordinates", ok, limit=100)
    section("Unused entries in coordinates.csv (not seen this run)", unused_in_coords)

    write_text(dated_md, "".join(md))

    # stable copies
    write_text(os.path.join(args.out_dir, "stops_report_latest.md"), "".join(md))
    write_csv(os.path.join(args.out_dir, "stops_report_latest.csv"),
              ["location_name", "status", "lat", "lon"], rows)

    print(f"Wrote {dated_md}")
    print(f"Wrote {dated_csv}")


if __name__ == "__main__":
    main()