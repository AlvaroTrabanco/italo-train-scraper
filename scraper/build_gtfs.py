#!/usr/bin/env python3
import argparse
import csv
import json
import os
import zipfile
from typing import Dict, Any, List, Tuple, Set
from datetime import datetime, timedelta, timezone

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


def normalize_arr_dep(arr: str, dep: str) -> Tuple[str, str]:
    """
    GTFS validator expects both arrival_time and departure_time.
    If one is missing, copy the other.
    """
    arr = (arr or "").strip()
    dep = (dep or "").strip()

    if arr and not dep:
        dep = arr
    elif dep and not arr:
        arr = dep

    return arr, dep


def main() -> None:
    ap = argparse.ArgumentParser(description="Build a minimal GTFS zip from normalized Italo schedules.")
    ap.add_argument("--normalized-dir", required=True, help="Directory with *.normalized.json files")
    ap.add_argument("--service-date", required=True, help="YYYYMMDD (single-day service for this export)")
    ap.add_argument("--out-zip", required=True, help="Output GTFS zip path")
    ap.add_argument("--agency-name", default="Italo", help="agency_name")
    ap.add_argument("--agency-id", default="ITALO", help="agency_id")
    args = ap.parse_args()

    coords_by_name = load_coords_csv("coordinates.csv")

    service_id = f"SVC_{args.service_date}"
    agency_id = args.agency_id

    # Service window: start at --service-date and run for 1 year (inclusive)
    start_date = args.service_date  # still start service on the service-date
    today_utc = datetime.now(timezone.utc).date()
    end_date = (today_utc + timedelta(days=365)).strftime("%Y%m%d")

    norm_files = [f for f in os.listdir(args.normalized_dir) if f.endswith(".normalized.json")]
    if not norm_files:
        raise SystemExit("No normalized files found")

    # stops: we only emit stops that are referenced by kept stop_times
    stop_id_by_key: Dict[str, str] = {}
    stops_rows: List[List[str]] = []
    seen_stop_ids: Set[str] = set()

    # routes / trips / stop_times
    routes_rows: List[List[str]] = []
    trips_rows: List[List[str]] = []
    stop_times_rows: List[List[str]] = []

    # Track which routes actually have >=1 kept trip
    used_route_ids: Set[str] = set()

    # Minimal agency.txt
    agency_txt = [
        ["agency_id", "agency_name", "agency_url", "agency_timezone"],
        [agency_id, args.agency_name, "https://www.italotreno.com/", "Europe/Rome"],
    ]

    # calendar: trips valid every day for 1 year starting at --service-date
    # monday..sunday = 1 means runs daily
    calendar_rows = [[service_id, "1", "1", "1", "1", "1", "1", "1", start_date, end_date]]

    def stop_key(code: str, name: str) -> str:
        code = (code or "").strip()
        name = (name or "").strip()
        return code or name

    def coords_for_name(name: str) -> Tuple[str, str]:
        name = (name or "").strip()
        lat, lon = coords_by_name.get(name, ("", ""))
        return (lat, lon)

    def keep_stop(name: str) -> bool:
        lat, lon = coords_for_name(name)
        return has_valid_coord(lat, lon)

    def ensure_stop(code: str, name: str) -> str:
        """
        Only called for stops we are keeping.
        Ensures the stop exists in stops_rows.
        """
        key = stop_key(code, name)
        if not key:
            # Extremely defensive: should not happen, but keep deterministic output
            key = "UNKNOWN"

        if key in stop_id_by_key:
            return stop_id_by_key[key]

        stop_id = f"STOP_{key}"
        stop_id_by_key[key] = stop_id

        if stop_id not in seen_stop_ids:
            seen_stop_ids.add(stop_id)

            stop_name = (name or key).strip() or key
            stop_code = (code or "").strip()
            lat, lon = coords_for_name(stop_name)

            # At this point we expect valid coords; but keep defensive
            if not has_valid_coord(lat, lon):
                lat, lon = ("", "")

            stops_rows.append([stop_id, stop_name, lat, lon, stop_code])

        return stop_id

    dropped_stops_no_coords = 0
    dropped_trips_too_few_stops = 0

    for fn in sorted(norm_files):
        data = load_json(os.path.join(args.normalized_dir, fn))

        train = data["train_number"]
        origin = data.get("origin_station") or ""
        dest = data.get("destination_station") or ""

        route_id = f"R_{train}"
        trip_id = f"T_{train}_{args.service_date}"

        # Build stop_times for this trip, skipping stops without coords and reindexing sequences
        kept_rows_for_trip: List[List[str]] = []
        seq = 0

        for s in data.get("stops", []):
            name = (s.get("stop_name") or "").strip()
            code = (s.get("location_code") or "").strip()

            if not name:
                continue

            if not keep_stop(name):
                dropped_stops_no_coords += 1
                continue

            stop_id = ensure_stop(code, name)

            arr = s.get("arrival_time") or ""
            dep = s.get("departure_time") or ""
            arr, dep = normalize_arr_dep(arr, dep)

            kept_rows_for_trip.append([trip_id, arr, dep, stop_id, str(seq)])
            seq += 1

        # If fewer than 2 stops remain, drop the entire trip (and thus its stop_times)
        if len(kept_rows_for_trip) < 2:
            dropped_trips_too_few_stops += 1
            continue

        # Keep trip
        used_route_ids.add(route_id)

        # routes.txt row is "one per train number", but only keep if used
        # We'll append now and filter later, or just append only when used.
        routes_rows.append([route_id, agency_id, str(train), f"{origin} – {dest}", "2"])
        trips_rows.append([route_id, service_id, trip_id, str(train)])
        stop_times_rows.extend(kept_rows_for_trip)

    # Filter routes_rows down to used routes (avoid duplicates too)
    # routes_rows currently has one row per kept trip; dedupe by route_id
    dedup_routes: Dict[str, List[str]] = {}
    for r in routes_rows:
        rid = r[0]
        if rid in used_route_ids:
            dedup_routes[rid] = r
    routes_rows = [dedup_routes[rid] for rid in sorted(dedup_routes.keys())]

    # Write txt files to a temp folder, zip them
    tmp = os.path.join(args.normalized_dir, "__gtfs_tmp__")
    os.makedirs(tmp, exist_ok=True)

    write_csv(os.path.join(tmp, "agency.txt"), agency_txt[0], [agency_txt[1]])
    write_csv(
        os.path.join(tmp, "stops.txt"),
        ["stop_id", "stop_name", "stop_lat", "stop_lon", "stop_code"],
        stops_rows,
    )
    write_csv(
        os.path.join(tmp, "routes.txt"),
        ["route_id", "agency_id", "route_short_name", "route_long_name", "route_type"],
        routes_rows,
    )
    write_csv(
        os.path.join(tmp, "trips.txt"),
        ["route_id", "service_id", "trip_id", "trip_short_name"],
        trips_rows,
    )
    write_csv(
        os.path.join(tmp, "stop_times.txt"),
        ["trip_id", "arrival_time", "departure_time", "stop_id", "stop_sequence"],
        stop_times_rows,
    )
    write_csv(
        os.path.join(tmp, "calendar.txt"),
        ["service_id", "monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday", "start_date", "end_date"],
        calendar_rows,
    )
    write_csv(
        os.path.join(tmp, "feed_info.txt"),
        ["feed_publisher_name", "feed_publisher_url", "feed_lang", "feed_start_date", "feed_end_date"],
        [[args.agency_name, "https://www.italotreno.com/", "it", start_date, end_date]],
    )

    os.makedirs(os.path.dirname(args.out_zip) or ".", exist_ok=True)
    with zipfile.ZipFile(args.out_zip, "w", compression=zipfile.ZIP_DEFLATED) as z:
        for name in [
            "agency.txt",
            "stops.txt",
            "routes.txt",
            "trips.txt",
            "stop_times.txt",
            "calendar.txt",
            "feed_info.txt",
        ]:
            z.write(os.path.join(tmp, name), arcname=name)

    print(f"Wrote {args.out_zip} with {len(trips_rows)} trips")
    print(f"Dropped stop_times rows (missing coords): {dropped_stops_no_coords}")
    print(f"Dropped trips (<2 stops after filtering): {dropped_trips_too_few_stops}")


if __name__ == "__main__":
    main()