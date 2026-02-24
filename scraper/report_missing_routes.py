#!/usr/bin/env python3
import argparse
import csv
import os
import re
import zipfile
from dataclasses import dataclass
from typing import Dict, List, Tuple, Optional


def pick_train_col(headers: List[str]) -> Optional[str]:
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

    for h in headers:
        if h and h.strip().lower() in candidates:
            return h

    for h in headers:
        if not h:
            continue
        hn = re.sub(r"\s+", " ", h.strip().lower())
        if hn in candidates:
            return h

    if len(headers) >= 3:
        return headers[2]

    return None


def pretty_trains(s: str) -> str:
    parts = [p.strip() for p in (s or "").split(",") if p.strip()]
    return ", ".join(parts)


def norm(s: str) -> str:
    return re.sub(r"\s+", " ", (s or "").strip().lower())


def read_gtfs_routes_from_zip(zip_path: str) -> List[Dict[str, str]]:
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

        dep_keys = ["Departure_mapped", "From_mapped", "Departure", "From"]
        arr_keys = ["Arrival_mapped", "To_mapped", "Arrival", "To"]

        def pick_col(keys: List[str]) -> Optional[str]:
            for k in keys:
                if k in headers:
                    return k
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
            raise SystemExit(f"Expected file must contain Departure/Arrival columns.")

        out: List[Dict[str, str]] = []
        for row in reader:
            dep = (row.get(dep_col) or "").strip()
            arr = (row.get(arr_col) or "").strip()
            if not dep and not arr:
                continue

            exp_trains = (row.get(trains_col) or "").strip() if trains_col else ""
            exp_trains = pretty_trains(exp_trains)

            out.append({
                "departure": dep,
                "arrival": arr,
                "expected_trains": exp_trains
            })

        return out


@dataclass
class MatchRow:
    departure: str
    arrival: str
    status: str
    expected_trains: str
    found_trains: str
    missing_anywhere: str
    missing_under_this_ab: str
    present_elsewhere: str
    extra_gtfs_trains: str


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--expected-csv", required=True)
    ap.add_argument("--gtfs-zip", required=True)
    ap.add_argument("--out-dir", required=True)
    ap.add_argument("--out-prefix", default="missing_routes")
    args = ap.parse_args()

    os.makedirs(args.out_dir, exist_ok=True)

    expected = load_expected_csv(args.expected_csv)
    gtfs_routes = read_gtfs_routes_from_zip(args.gtfs_zip)

    # Global train index
    train_to_longnames: Dict[str, set] = {}
    for r in gtfs_routes:
        t = (r.get("route_short_name","") or "").strip()
        ln = (r.get("route_long_name","") or "").strip()
        if t:
            train_to_longnames.setdefault(t, set()).add(ln)

    # A→B index
    idx: Dict[Tuple[str,str], List[str]] = {}
    for r in gtfs_routes:
        ln = r.get("route_long_name","") or ""
        short = (r.get("route_short_name","") or "").strip()
        a,b = parse_route_long_name(ln)
        key = (norm(a), norm(b))
        idx.setdefault(key, []).append(short)

    results: List[MatchRow] = []

    for e in expected:
        dep = e["departure"]
        arr = e["arrival"]
        expected_set = set([t.strip() for t in e["expected_trains"].split(",") if t.strip()])

        key = (norm(dep), norm(arr))
        found_under_ab = set(idx.get(key, []))

        # Missing completely
        missing_anywhere = sorted([t for t in expected_set if t not in train_to_longnames])

        # Missing only under this AB
        missing_under_this_ab = sorted([t for t in expected_set if t not in found_under_ab])

        # Present elsewhere
        present_elsewhere = []
        for t in expected_set:
            if t in train_to_longnames and t not in found_under_ab:
                present_elsewhere.append(
                    f"{t} ({' | '.join(sorted(train_to_longnames[t]))})"
                )

        extra_gtfs = sorted(found_under_ab - expected_set)

        if not found_under_ab:
            status = "MISSING_ROUTE"
        elif missing_under_this_ab:
            status = "PARTIAL_MISSING"
        else:
            status = "OK"

        results.append(
            MatchRow(
                departure=dep,
                arrival=arr,
                status=status,
                expected_trains=", ".join(sorted(expected_set)),
                found_trains=", ".join(sorted(found_under_ab)),
                missing_anywhere=", ".join(missing_anywhere),
                missing_under_this_ab=", ".join(missing_under_this_ab),
                present_elsewhere=" ; ".join(present_elsewhere),
                extra_gtfs_trains=", ".join(extra_gtfs),
            )
        )

    # CSV
    csv_path = os.path.join(args.out_dir, f"{args.out_prefix}_latest.csv")
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow([
            "departure","arrival","status",
            "expected_trains","found_trains",
            "missing_anywhere",
            "missing_under_this_ab",
            "present_elsewhere",
            "extra_gtfs_trains"
        ])
        for r in results:
            w.writerow([
                r.departure,
                r.arrival,
                r.status,
                r.expected_trains,
                r.found_trains,
                r.missing_anywhere,
                r.missing_under_this_ab,
                r.present_elsewhere,
                r.extra_gtfs_trains
            ])

    # Markdown
    md_path = os.path.join(args.out_dir, f"{args.out_prefix}_latest.md")
    with open(md_path, "w", encoding="utf-8") as f:
        f.write("# Missing routes report\n\n")
        f.write("| departure | arrival | status | expected | found | missing anywhere | missing under this A–B | present elsewhere | extra |\n")
        f.write("|---|---|---|---|---|---|---|---|---|\n")

        for r in results:
            f.write(
                f"| {r.departure} | {r.arrival} | {r.status} | "
                f"{r.expected_trains} | {r.found_trains} | "
                f"{r.missing_anywhere} | {r.missing_under_this_ab} | "
                f"{r.present_elsewhere} | {r.extra_gtfs_trains} |\n"
            )

    print("Report generated.")
    

if __name__ == "__main__":
    main()