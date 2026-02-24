#!/usr/bin/env python3
import argparse
import csv
import os
import re
import zipfile
from dataclasses import dataclass
from typing import Dict, List, Tuple, Optional


def pick_train_col(headers: List[str]) -> Optional[str]:
    """
    Robustly detect the 'train numbers' column in expected_routes_mapped.csv.
    Accepts a variety of header names; falls back to 3rd column if present.
    """
    if not headers:
        return None

    candidates = {
        "train_numbers",
        "train number",
        "train numbers",
        "line number",
        "line numbers",
        "line_number",
        "line_numbers",
        "trains",
        "train",
    }

    # Exact match (case-insensitive)
    for h in headers:
        if h and h.strip().lower() in candidates:
            return h

    # Normalized match (whitespace/casing)
    for h in headers:
        if not h:
            continue
        hn = re.sub(r"\s+", " ", h.strip().lower())
        if hn in candidates:
            return h

    # Fallback: 3rd column if file has >= 3 columns
    if len(headers) == 3:
        return headers[2]

    return None


def pretty_trains(s: str) -> str:
    """
    Normalize train lists like '9991,9977,9931' -> '9991, 9977, 9931'
    """
    parts = [p.strip() for p in (s or "").split(",") if p.strip()]
    return ", ".join(parts)

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
    if not os.path.exists(path):
        raise SystemExit(f"Expected routes csv not found: {path}")

    with open(path, "r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        headers = reader.fieldnames or []

        # departure/arrival columns (mapped preferred)
        dep_keys = ["Departure_mapped", "From_mapped", "Departure", "From"]
        arr_keys = ["Arrival_mapped", "To_mapped", "Arrival", "To"]

        def pick_col(keys: List[str]) -> Optional[str]:
            for k in keys:
                if k in headers:
                    return k
            # case-insensitive fallback
            lower_map = {h.lower(): h for h in headers if h}
            for k in keys:
                hk = lower_map.get(k.lower())
                if hk:
                    return hk
            return None

        dep_col = pick_col(dep_keys)
        arr_col = pick_col(arr_keys)
        trains_col = pick_train_col(headers)

        if not dep_col or not arr_col:
            raise SystemExit(
                f"Expected file must contain Departure/Arrival (or *_mapped). Found headers: {headers}"
            )

        out: List[Dict[str, str]] = []
        for row in reader:
            dep = (row.get(dep_col) or "").strip()
            arr = (row.get(arr_col) or "").strip()
            if not dep and not arr:
                continue

            exp_trains = (row.get(trains_col) or "").strip() if trains_col else ""
            exp_trains = pretty_trains(exp_trains)

            out.append({"departure": dep, "arrival": arr, "expected_trains": exp_trains})

        return out


@dataclass
class MatchRow:
    departure: str
    arrival: str
    status: str
    trains: str                  # trains found in GTFS
    expected_trains: str         # trains from expected CSV
    gtfs_route_long_names: str
    missing_trains: str


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
    partial_count = 0

    for e in expected:
        dep = e["departure"]
        arr = e["arrival"]
        exp_trains = e.get("expected_trains", "")
        key = (norm(dep), norm(arr))
        matches = idx.get(key, [])

        expected_set = set([t.strip() for t in exp_trains.split(",") if t.strip()])

        gtfs_set = set()
        long_names = []

        for m in matches:
            if m["train"]:
                gtfs_set.add(m["train"])
            if m["long_name"]:
                long_names.append(m["long_name"])

        missing_trains = expected_set - gtfs_set
        extra_trains = gtfs_set - expected_set

        if not matches:
            status = "MISSING_ROUTE"
            missing_count += 1
        elif missing_trains:
            status = "PARTIAL_MISSING"
            partial_count += 1
        else:
            status = "OK"

        missing_trains_str = ", ".join(sorted(missing_trains))
        
        results.append(
            MatchRow(
                departure=dep,
                arrival=arr,
                status=status,
                trains=", ".join(sorted(gtfs_set)),
                expected_trains=", ".join(sorted(expected_set)),
                gtfs_route_long_names=" | ".join(sorted(set(long_names))),
                missing_trains=missing_trains_str,
            )
        )

    # Write CSV
    csv_path = os.path.join(args.out_dir, f"{args.out_prefix}_latest.csv")
    with open(csv_path, "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["departure","arrival","status","expected_trains","trains","missing_trains","gtfs_route_long_names"])
        for r in results:
            w.writerow([r.departure, r.arrival, r.status, r.expected_trains, r.trains, r.missing_trains, r.gtfs_route_long_names])

    # Write Markdown
    md_path = os.path.join(args.out_dir, f"{args.out_prefix}_latest.md")
    with open(md_path, "w", encoding="utf-8") as f:
        f.write("# Missing routes report\n\n")
        f.write(f"- Expected pairs: **{len(results)}**\n")
        f.write(f"- Missing routes (no A→B in GTFS): **{missing_count}**\n")
        f.write(f"- Partial routes (some trains missing): **{partial_count}**\n\n")

        f.write("## Missing or Partial\n\n")
        f.write("| departure | arrival | status | expected_trains | found_trains | missing_trains |\n|---|---|---|---|---|---|\n")
        for r in results:
            if r.status in ("MISSING_ROUTE", "PARTIAL_MISSING"):
                f.write(f"| {r.departure} | {r.arrival} | {r.status} | {r.expected_trains} | {r.trains} | {r.missing_trains} |\n")

        f.write("\n## OK (all expected trains found)\n\n")
        f.write("| departure | arrival | found_trains | expected_trains |\n|---|---|---|---|\n")
        for r in results:
            if r.status == "OK":
                f.write(f"| {r.departure} | {r.arrival} | {r.trains} | {r.expected_trains} | {r.missing_trains} |\n")

    print(f"Wrote:\n- {csv_path}\n- {md_path}\nMissing count: {missing_count}")


if __name__ == "__main__":
    main()