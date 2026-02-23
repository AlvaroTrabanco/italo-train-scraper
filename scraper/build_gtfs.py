#!/usr/bin/env python3
import argparse
import csv
import json
import os
import zipfile
from datetime import datetime
from typing import Dict, Any, List, Tuple, Set, Optional

def load_coords_csv(path: str) -> Dict[str, Tuple[str, str]]:
    coords: Dict[str, Tuple[str, str]] = {}
    if not os.path.exists(path):
        return coords
    with open(path, "r", encoding="utf-8", newline="") as f:
        r = csv.DictReader(f)
        for row in r:
            name = (row.get("location_name") or "").strip()
            lat = (row.get("lat") or "").strip()
            lon = (row.get("lon") or "").strip()
            if not name:
                continue
            coords[name] = (lat, lon)
    return coords

def load_json(path: str) -> Dict[str, Any]:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def write_csv(path: str, header: List[str], rows: List[List[str]]) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(header)
        w.writerows(rows)

def has_valid_coord(lat: str, lon: str) -> bool:
    """Return True if lat/lon are parseable and in valid ranges."""
    try:
        if lat == "" or lon == "":
            return False
        la = float(lat)
        lo = float(lon)
        return -90 <= la <= 90 and -180 <= lo <= 180
    except Exception:
        return False

def main() -> None:
    ap = argparse.ArgumentParser(description="Build a minimal GTFS zip from normalized Italo schedules.")
    ap.add_argument("--normalized-dir", required=True, help="Directory with *.normalized.json files")
    ap.add_argument("--service-date", required=True, help="YYYYMMDD (single-day service for this export)")
    ap.add_argument("--out-zip", required=True, help="Output GTFS zip path")
    ap.add_argument("--agency-name", default="Italo", help="agency_name")
    ap.add_argument("--agency-id", default="ITALO", help="agency_id")
    ap.add_argument("--coordinates", default="coordinates.csv", help="coordinates.csv path (optional)")
    args = ap.parse_args()
    
    # Load optional stop coordinates (filled manually)
    coords_by_name = load_coords_csv(args.coordinates)

    service_id = f"SVC_{args.service_date}"
    agency_id = args.agency_id

    norm_files = [f for f in os.listdir(args.normalized_dir) if f.endswith(".normalized.json")]
    if not norm_files:
        raise SystemExit("No normalized files found")

    # Collect stops
    stop_id_by_code: Dict[str, str] = {}
    stops_rows: List[List[str]] = []
    seen_stops: Set[str] = set()
    stop_code_by_stop_id: Dict[str, str] = {}
    stop_latlon_by_stop_id: Dict[str, Tuple[str, str]] = {}

    # Routes/Trips/Stop_times
    routes_rows: List[List[str]] = []
    trips_rows: List[List[str]] = []
    stop_times_rows: List[List[str]] = []

    # Minimal agency.txt
    agency_txt = [
        ["agency_id", "agency_name", "agency_url", "agency_timezone"],
        [agency_id, args.agency_name, "https://www.italotreno.com/", "Europe/Rome"],
    ]

    # calendar_dates: all trips valid on one service date
    cal_dates_rows = [[service_id, args.service_date, "1"]]

    def ensure_stop(code: str, name: str) -> Optional[str]:
        """
        Return stop_id if the stop has valid coordinates; otherwise return None.
        Uses code (preferred) or name as stable key.
        """
        key = code or name
        if key in stop_id_by_code:
            return stop_id_by_code[key]

        stop_name = (name or key).strip() or key
        stop_code = (code or "").strip()

        # Coordinates are keyed by location_name in coordinates.csv
        lat, lon = coords_by_name.get(stop_name, ("", ""))

        # HARD RULE: do not include stops without valid coordinates
        if not has_valid_coord(lat, lon):
            return None

        stop_id = f"STOP_{key}"
        stop_id_by_code[key] = stop_id

        if stop_id not in seen_stops:
            seen_stops.add(stop_id)
            stop_latlon_by_stop_id[stop_id] = (lat, lon)
            stop_code_by_stop_id[stop_id] = stop_code
            stops_rows.append([stop_id, stop_name, lat, lon, stop_code])

        return stop_id

    for f in sorted(norm_files):
        data = load_json(os.path.join(args.normalized_dir, f))
        train = data.get("train_number")
        if not train:
            continue
        origin = data.get("origin_station") or ""
        dest = data.get("destination_station") or ""
        route_id = f"R_{train}"
        trip_id = f"T_{train}_{args.service_date}"

        # Build stop_times for this trip, but SKIP stops with missing coords
        trip_stop_times: List[List[str]] = []
        seq = 0

        for s in data.get("stops", []):
            name = (s.get("stop_name") or "").strip()
            code = (s.get("location_code") or "").strip()

            stop_id = ensure_stop(code, name)
            if stop_id is None:
                # drop this stop entirely
                continue

            arr = s.get("arrival_time") or ""
            dep = s.get("departure_time") or ""
            trip_stop_times.append([trip_id, arr, dep, stop_id, str(seq)])
            seq += 1

        # If filtering removed too many stops, drop the trip entirely (needs at least 2 stops)
        if len(trip_stop_times) < 2:
            continue

        # routes.txt (one route per train number)
        routes_rows.append([route_id, agency_id, str(train), f"{origin} – {dest}", "2"])

        # trips.txt
        trips_rows.append([route_id, service_id, trip_id, str(train)])

        # stop_times.txt
        stop_times_rows.extend(trip_stop_times)

    # Write txt files to a temp folder, zip them
    tmp = os.path.join(args.normalized_dir, "__gtfs_tmp__")
    os.makedirs(tmp, exist_ok=True)

    write_csv(os.path.join(tmp, "agency.txt"), agency_txt[0], [agency_txt[1]])
    write_csv(
        os.path.join(tmp, "stops.txt"),
        ["stop_id", "stop_name", "stop_lat", "stop_lon", "stop_code"],
        stops_rows
    )
    write_csv(os.path.join(tmp, "routes.txt"),
              ["route_id", "agency_id", "route_short_name", "route_long_name", "route_type"],
              routes_rows)
    write_csv(os.path.join(tmp, "trips.txt"),
              ["route_id", "service_id", "trip_id", "trip_short_name"],
              trips_rows)
    write_csv(os.path.join(tmp, "stop_times.txt"),
              ["trip_id", "arrival_time", "departure_time", "stop_id", "stop_sequence"],
              stop_times_rows)
    write_csv(os.path.join(tmp, "calendar_dates.txt"),
              ["service_id", "date", "exception_type"],
              cal_dates_rows)

    with zipfile.ZipFile(args.out_zip, "w", compression=zipfile.ZIP_DEFLATED) as z:
        for name in ["agency.txt", "stops.txt", "routes.txt", "trips.txt", "stop_times.txt", "calendar_dates.txt"]:
            z.write(os.path.join(tmp, name), arcname=name)

    print(f"Wrote {args.out_zip} with {len(trips_rows)} trips")

if __name__ == "__main__":
    main()