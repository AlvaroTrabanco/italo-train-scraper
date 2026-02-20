#!/usr/bin/env python3
"""
Cumulative stop/coordinates reporting.

This script supports two modes:
- Per-run (no inventory): compares coordinates.csv to stops observed in the current normalized dir.
- Cumulative (inventory): loads a persistent stop inventory, merges current observed stops, writes updated inventory,
  and generates reports based on the cumulative inventory (so “unused” doesn’t fluctuate run-to-run).

Outputs (in --out-dir):
- stops_report_<run_utc>.md
- stops_report_<run_utc>.csv
- stops_report_latest.md
- stops_report_latest.csv
- (optional) stop_inventory.json (if --inventory-out provided)
"""

import argparse
import csv
import json
import os
from datetime import datetime, timezone
from typing import Dict, Any, Set, Tuple, List, Optional


# ---------- IO helpers ----------

def load_coords_csv(path: str) -> Dict[str, Tuple[str, str]]:
    """Load coordinates.csv mapping: location_name -> (lat, lon) as strings."""
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


def load_json_optional(path: str) -> Optional[Dict[str, Any]]:
    if not path or not os.path.exists(path):
        return None
    try:
        return load_json(path)
    except Exception:
        return None


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


def write_json(path: str, payload: Dict[str, Any]) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)


# ---------- Time helpers ----------

def parse_run_utc(run_utc: str) -> Optional[datetime]:
    """
    Parse run_utc like 20260220T083254Z -> aware datetime UTC.
    Returns None if parsing fails.
    """
    try:
        return datetime.strptime(run_utc, "%Y%m%dT%H%M%SZ").replace(tzinfo=timezone.utc)
    except Exception:
        return None


def fmt_dt(dt: Optional[datetime]) -> str:
    if not dt:
        return ""
    return dt.strftime("%Y%m%dT%H%M%SZ")


def hours_since(now: datetime, past: Optional[datetime]) -> Optional[float]:
    if not past:
        return None
    delta = now - past
    return delta.total_seconds() / 3600.0


# ---------- Domain logic ----------

def has_valid_coord(lat: str, lon: str) -> bool:
    try:
        if lat == "" or lon == "":
            return False
        la = float(lat)
        lo = float(lon)
        return -90 <= la <= 90 and -180 <= lo <= 180
    except Exception:
        return False


def collect_observed_stops(norm_dir: str) -> Tuple[Set[str], int]:
    """
    Collect unique stop_name values from normalized JSON files in a run directory.
    Returns (observed_stop_names, normalized_files_count).
    """
    observed: Set[str] = set()
    trains_ok = 0

    for path in iter_normalized_files(norm_dir):
        trains_ok += 1
        data = load_json(path)
        for s in data.get("stops", []):
            name = (s.get("stop_name") or "").strip()
            if name:
                observed.add(name)

    return observed, trains_ok


def load_inventory(path: Optional[str]) -> Dict[str, Dict[str, Any]]:
    """
    Inventory format:
      {
        "<Stop Name>": {"first_seen_utc": "...", "last_seen_utc": "...", "seen_count": 3}
      }
    """
    if not path:
        return {}
    payload = load_json_optional(path)
    if not payload or not isinstance(payload, dict):
        return {}
    inv: Dict[str, Dict[str, Any]] = {}
    for k, v in payload.items():
        if not isinstance(k, str) or not isinstance(v, dict):
            continue
        inv[k] = {
            "first_seen_utc": str(v.get("first_seen_utc") or ""),
            "last_seen_utc": str(v.get("last_seen_utc") or ""),
            "seen_count": int(v.get("seen_count") or 0),
        }
    return inv


def merge_inventory(
    inventory: Dict[str, Dict[str, Any]],
    observed: Set[str],
    run_utc: str
) -> Dict[str, Dict[str, Any]]:
    """
    Merge observed stops from current run into inventory, updating first_seen/last_seen and seen_count.
    """
    for name in observed:
        if name not in inventory:
            inventory[name] = {"first_seen_utc": run_utc, "last_seen_utc": run_utc, "seen_count": 1}
        else:
            entry = inventory[name]
            if not entry.get("first_seen_utc"):
                entry["first_seen_utc"] = run_utc
            entry["last_seen_utc"] = run_utc
            entry["seen_count"] = int(entry.get("seen_count") or 0) + 1
    return inventory


def categorize_against_inventory(
    coords: Dict[str, Tuple[str, str]],
    inventory: Dict[str, Dict[str, Any]],
    now_utc: datetime,
    window_hours: Optional[int],
) -> Dict[str, List[str]]:
    """
    Categorize using cumulative inventory.

    Returns dict with keys:
      - has_coordinates
      - missing_coordinates
      - new_not_in_coordinates  (in inventory but not in coordinates.csv)
      - unused_in_coordinates   (in coordinates.csv but never seen in inventory)
      - stale_inventory         (in inventory but not seen within window_hours) [optional]
    """
    inv_names = set(inventory.keys())
    coord_names = set(coords.keys())

    has_coords: List[str] = []
    missing_coords: List[str] = []
    new_not_in_coords: List[str] = []
    unused_in_coords: List[str] = []
    stale: List[str] = []

    # Inventory -> coords coverage
    for name in sorted(inv_names, key=lambda x: x.casefold()):
        if name not in coords:
            new_not_in_coords.append(name)
        else:
            lat, lon = coords[name]
            if has_valid_coord(lat, lon):
                has_coords.append(name)
            else:
                missing_coords.append(name)

        # stale check
        if window_hours is not None:
            last_seen = parse_run_utc(str(inventory[name].get("last_seen_utc") or ""))
            hs = hours_since(now_utc, last_seen)
            if hs is None or hs > window_hours:
                stale.append(name)

    # Coords entries never seen in inventory
    for name in sorted(coord_names - inv_names, key=lambda x: x.casefold()):
        unused_in_coords.append(name)

    out: Dict[str, List[str]] = {
        "has_coordinates": has_coords,
        "missing_coordinates": missing_coords,
        "new_not_in_coordinates": new_not_in_coords,
        "unused_in_coordinates": unused_in_coords,
    }
    if window_hours is not None:
        out["stale_inventory"] = stale
    return out


def build_rows_from_inventory(
    coords: Dict[str, Tuple[str, str]],
    inventory: Dict[str, Dict[str, Any]],
    window_hours: Optional[int],
    now_utc: datetime,
) -> List[List[str]]:
    """
    Build CSV rows for ALL inventory stops.
    Columns:
      location_name, status, lat, lon, first_seen_utc, last_seen_utc, seen_count, stale
    """
    rows: List[List[str]] = []
    for name in sorted(inventory.keys(), key=lambda x: x.casefold()):
        entry = inventory[name]
        first_seen = str(entry.get("first_seen_utc") or "")
        last_seen = str(entry.get("last_seen_utc") or "")
        seen_count = str(int(entry.get("seen_count") or 0))

        lat = lon = ""
        if name in coords:
            lat, lon = coords[name]
            status = "HAS_COORDINATES" if has_valid_coord(lat, lon) else "MISSING_COORDINATES"
        else:
            status = "NEW_NOT_IN_COORDINATES"

        stale_flag = ""
        if window_hours is not None:
            last_dt = parse_run_utc(last_seen)
            hs = hours_since(now_utc, last_dt)
            stale_flag = "YES" if (hs is None or hs > window_hours) else "NO"

        rows.append([name, status, lat, lon, first_seen, last_seen, seen_count, stale_flag])
    return rows


# ---------- Main ----------

def main() -> None:
    ap = argparse.ArgumentParser(description="Report coordinate coverage for Italo stops (supports cumulative inventory).")
    ap.add_argument("--normalized-dir", required=True, help="normalized/<run_utc> directory")
    ap.add_argument("--coordinates", default="coordinates.csv", help="coordinates.csv path")
    ap.add_argument("--out-dir", required=True, help="Output folder for report (e.g. public/reports)")
    ap.add_argument("--run-utc", required=True, help="Run identifier (folder name) like 20260220T083254Z")

    # Inventory persistence (optional)
    ap.add_argument("--inventory-in", default="", help="Existing stop_inventory.json to load (optional)")
    ap.add_argument("--inventory-out", default="", help="Where to write updated stop_inventory.json (optional)")

    # Staleness window (optional)
    ap.add_argument("--window-hours", type=int, default=0,
                    help="If >0, mark inventory stops as stale when not seen within this many hours (e.g. 168 for 7 days).")

    args = ap.parse_args()

    coords = load_coords_csv(args.coordinates)
    observed, trains_ok = collect_observed_stops(args.normalized_dir)

    # Determine now based on run_utc if possible; else current UTC
    run_dt = parse_run_utc(args.run_utc)
    now_utc = run_dt or datetime.now(timezone.utc)

    # Load + merge inventory if requested
    inventory_in = args.inventory_in.strip() or None
    inventory_out = args.inventory_out.strip() or None
    inventory = load_inventory(inventory_in) if inventory_in else {}

    # Always merge current observed into inventory if inventory_out is set OR inventory_in exists
    use_inventory = bool(inventory_in or inventory_out)
    if use_inventory:
        inventory = merge_inventory(inventory, observed, args.run_utc)
        if inventory_out:
            write_json(inventory_out, inventory)

    window_hours: Optional[int] = args.window_hours if args.window_hours and args.window_hours > 0 else None

    # If not using inventory, treat "inventory" as just this run's observed set
    if not use_inventory:
        # synthesize inventory from observed for consistent reporting outputs
        inventory = {name: {"first_seen_utc": args.run_utc, "last_seen_utc": args.run_utc, "seen_count": 1} for name in observed}

    cats = categorize_against_inventory(coords, inventory, now_utc, window_hours)

    # Build CSV for inventory stops
    rows = build_rows_from_inventory(coords, inventory, window_hours, now_utc)

    out_dir = args.out_dir
    os.makedirs(out_dir, exist_ok=True)

    dated_csv = os.path.join(out_dir, f"stops_report_{args.run_utc}.csv")
    dated_md = os.path.join(out_dir, f"stops_report_{args.run_utc}.md")
    latest_csv = os.path.join(out_dir, "stops_report_latest.csv")
    latest_md = os.path.join(out_dir, "stops_report_latest.md")

    csv_header = ["location_name", "status", "lat", "lon", "first_seen_utc", "last_seen_utc", "seen_count", "stale"]
    write_csv(dated_csv, csv_header, rows)
    write_csv(latest_csv, csv_header, rows)

    # Markdown summary
    md: List[str] = []
    md.append("# Italo stops coordinates report\n\n")
    md.append(f"- Run: `{args.run_utc}`\n")
    md.append(f"- Normalized trains (ok): **{trains_ok}**\n")
    md.append(f"- Unique stops observed in this run: **{len(observed)}**\n")
    md.append(f"- Unique stops in inventory: **{len(inventory)}**\n")
    md.append(f"- Stops with coordinates: **{len(cats['has_coordinates'])}**\n")
    md.append(f"- Stops missing coordinates: **{len(cats['missing_coordinates'])}**\n")
    md.append(f"- New stops not in coordinates.csv: **{len(cats['new_not_in_coordinates'])}**\n")
    md.append(f"- Unused entries in coordinates.csv (never seen in inventory): **{len(cats['unused_in_coordinates'])}**\n")
    if window_hours is not None and "stale_inventory" in cats:
        md.append(f"- Stale inventory stops (not seen in last {window_hours}h): **{len(cats['stale_inventory'])}**\n")

    if use_inventory:
        md.append("\n_This report is **cumulative** (uses stop_inventory.json)._\n")
    else:
        md.append("\n_This report is **per-run** (no inventory provided)._\n")

    def section(title: str, items: List[str], limit: int = 200) -> None:
        md.append(f"\n## {title} ({len(items)})\n")
        if not items:
            md.append("_None_\n")
            return
        if len(items) > limit:
            md.append(f"_Showing first {limit} only. See CSV for full list._\n")
            items = items[:limit]
        for x in items:
            md.append(f"- {x}\n")

    section("Missing coordinates", cats["missing_coordinates"])
    section("New stops not in coordinates.csv", cats["new_not_in_coordinates"])
    section("Unused entries in coordinates.csv (never seen in inventory)", cats["unused_in_coordinates"])
    if window_hours is not None and "stale_inventory" in cats:
        section(f"Stale inventory (not seen within {window_hours} hours)", cats["stale_inventory"])
    section("Has coordinates", cats["has_coordinates"], limit=100)

    write_text(dated_md, "".join(md))
    write_text(latest_md, "".join(md))

    print(f"Wrote {dated_md}")
    print(f"Wrote {dated_csv}")
    if inventory_out:
        print(f"Wrote {inventory_out}")


if __name__ == "__main__":
    main()