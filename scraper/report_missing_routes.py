#!/usr/bin/env python3
import argparse
import csv
import os
import re
import zipfile
from dataclasses import dataclass
from typing import Dict, List, Tuple, Optional


def norm(s: str) -> str:
    return re.sub(r"\s+", " ", (s or "").strip().lower())


def read_gtfs_routes_from_zip(zip_path: str) -> List[Dict[str, str]]:
    """
    Reads routes.txt from the GTFS zip and returns rows as dicts.
    Expects: route_id, agency_id, route_short_name, route_long_name, route_type
    """
    if not os.path.exists(zip_path):
        raise SystemExit(f"GTFS zip not found: {zip_path}")

    with zipfile.ZipFile(zip_path, "r") as z:
        if "routes.txt" not in z.namelist():
            raise SystemExit(f"routes.txt not found inside: {zip_path}")
        raw = z.read("routes.txt").decode("utf-8", "replace").splitlines()

    if not raw:
        return []

    header = [h.strip() for h in raw[0].split(",")]
    rows: List[Dict[str, str]] = []
    for line in raw[1:]:
        parts = line.split(",")
        if len(parts) < len(header):
            parts += [""] * (len(header) - len(parts))
        d = {header[i]: (parts[i] if i < len(parts) else "") for i in range(len(header))}
        rows.append(d)
    return rows


def parse_route_long_name(route_long_name: str) -> Tuple[str, str]:
    """
    Your build_gtfs writes route_long_name as "{origin} – {dest}" (EN DASH).
    Fallbacks included.
    """
    s = (route_long_name or "").strip()
    if " – " in s:
        a, b = s.split(" – ", 1)
        return a.strip(), b.strip()
    if " - " in s:
        a, b = s.split(" - ", 1)
        return a.strip(), b.strip()
    return s.strip(), ""


def load_expected_csv(path: str) -> List[Dict[str, str]]:
    """
    Reads expected routes from CSV.
    Accepts columns:
      - Departure_mapped + Arrival_mapped (preferred)
      - or Departure + Arrival
      - or From + To
    """
    if not os.path.exists(path):
        raise SystemExit(f"Expected routes csv not found: {path}")

    with open(path, "r", encoding="utf-8-sig", newline="") as f:
        r = csv.DictReader(f)
        if not r.fieldnames:
            return []

        fields = [c.strip() for c in r.fieldnames]

        def pick(keys: List[str]) -> Optional[str]:
            for k in keys:
                if k in fields:
                    return k
            return None

        dep_col = pick(["Departure_mapped", "From_mapped", "Departure", "From"])
        arr_col = pick(["Arrival_mapped", "To_mapped", "Arrival", "To"])

        if not dep_col or not arr_col:
            raise SystemExit(
                "Expected CSV must contain Departure/Arrival columns (or *_mapped). "
                f"Found headers: {fields}"
            )

        out: List[Dict[str, str]] = []
        for row in r:
            dep = (row.get(dep_col) or "").strip()
            arr = (row.get(arr_col) or "").strip()
            if not dep and not arr:
                continue
            out.append({"departure": dep, "arrival": arr})
        return out


@dataclass
class MatchRow:
    departure: str
    arrival: str
    status: str
    trains: str
    gtfs_route_long_names: str


def main() -> None:
    ap = argparse.ArgumentParser(description="Compare expected A→B routes against GTFS routes.txt and output missing list.")
    ap.add_argument("--expected-csv", required=True, help="Path to expected routes CSV (exported from your xlsx)")
    ap.add_argument("--gtfs-zip", required=True, help="Path to GTFS zip (italo_latest.zip or dated zip)")
    ap.add_argument("--out-dir", required=True, help="Output directory (e.g. public/reports)")
    ap.add_argument("--out-prefix", default="missing_routes", help="Output basename prefix (default missing_routes)")
    args = ap.parse_args()

    os.makedirs(args.out_dir, exist_ok=True)

    expected = load_expected_csv(args.expected_csv)
    gtfs_routes = read_gtfs_routes_from_zip(args.gtfs_zip)

    # Index GTFS by normalized (origin,dest)
    idx: Dict[Tuple[str, str], List[Dict[str, str]]] = {}
    for r in gtfs_routes:
        long_name = r.get("route_long_name", "") or ""
        short = r.get("route_short_name", "") or ""  # train number in your feed
        a, b = parse_route_long_name(long_name)
        key = (norm(a), norm(b))
        idx.setdefault(key, []).append({"train": short.strip(), "long_name": long_name.strip()})

    results: List[MatchRow] = []
    missing_count = 0

    for e in expected:
        dep = e["departure"]
        arr = e["arrival"]
        key = (norm(dep), norm(arr))
        matches = idx.get(key, [])

        if matches:
            trains = sorted({m["train"] for m in matches if m["train"]})
            long_names = sorted({m["long_name"] for m in matches if m["long_name"]})
            results.append(
                MatchRow(
                    departure=dep,
                    arrival=arr,
                    status="OK",
                    trains=", ".join(trains),
                    gtfs_route_long_names=" | ".join(long_names),
                )
            )
        else:
            missing_count += 1
            results.append(
                MatchRow(
                    departure=dep,
                    arrival=arr,
                    status="MISSING_IN_GTFS",
                    trains="",
                    gtfs_route_long_names="",
                )
            )

    # Write CSV
    csv_path = os.path.join(args.out_dir, f"{args.out_prefix}_latest.csv")
    with open(csv_path, "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["departure", "arrival", "status", "trains", "gtfs_route_long_names"])
        for r in results:
            w.writerow([r.departure, r.arrival, r.status, r.trains, r.gtfs_route_long_names])

    # Write Markdown
    md_path = os.path.join(args.out_dir, f"{args.out_prefix}_latest.md")
    with open(md_path, "w", encoding="utf-8") as f:
        f.write("# Missing routes report\n\n")
        f.write(f"- Expected pairs: **{len(results)}**\n")
        f.write(f"- Missing in GTFS: **{missing_count}**\n\n")

        f.write("## Missing (Expected but not in GTFS)\n\n")
        f.write("| departure | arrival |\n|---|---|\n")
        for r in results:
            if r.status == "MISSING_IN_GTFS":
                f.write(f"| {r.departure} | {r.arrival} |\n")

        f.write("\n## Present (Expected and found in GTFS)\n\n")
        f.write("| departure | arrival | trains |\n|---|---|---|\n")
        for r in results:
            if r.status == "OK":
                f.write(f"| {r.departure} | {r.arrival} | {r.trains} |\n")

    print(f"Wrote:\n- {csv_path}\n- {md_path}\nMissing count: {missing_count}")


if __name__ == "__main__":
    main()