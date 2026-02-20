#!/usr/bin/env python3
import argparse
import json
import os
import re
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional


TIME_RE = re.compile(r"^\d{2}:\d{2}$")


def parse_hhmm(s: Optional[str]) -> Optional[int]:
    """Return minutes since 00:00 for HH:MM, else None."""
    if not s or not TIME_RE.match(s):
        return None
    hh, mm = s.split(":")
    return int(hh) * 60 + int(mm)


def fmt_gtfs_time(minutes: Optional[int]) -> Optional[str]:
    """Convert minutes since 00:00 (can exceed 1440) to HH:MM:SS with HH possibly >= 24."""
    if minutes is None:
        return None
    hh = minutes // 60
    mm = minutes % 60
    return f"{hh:02d}:{mm:02d}:00"


def infer_rollover_minutes(times: List[Optional[int]]) -> List[Optional[int]]:
    """
    If times go backwards (e.g. 23:50 -> 00:10), assume midnight rollover and add +24h from that point.
    Works on minutes list in stop sequence order.
    """
    out: List[Optional[int]] = []
    offset = 0
    prev: Optional[int] = None
    for t in times:
        if t is None:
            out.append(None)
            continue
        val = t + offset
        if prev is not None and val < prev:
            # rollover
            offset += 1440
            val = t + offset
        out.append(val)
        prev = val
    return out


def load_json(path: str) -> Dict[str, Any]:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def write_json(path: str, payload: Dict[str, Any]) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)


def extract_stops_from_train_schedule(raw: Dict[str, Any], train: str) -> Optional[Dict[str, Any]]:
    if not raw or raw.get("IsEmpty") or not raw.get("TrainSchedule"):
        return None

    ts = raw["TrainSchedule"]

    # gather stops: StazionePartenza, then StazioniFerme, then StazioniNonFerme
    stops_raw: List[Dict[str, Any]] = []

    def add(obj: Dict[str, Any]) -> None:
        if not obj:
            return
        stops_raw.append(obj)

    add(ts.get("StazionePartenza") or {})
    for s in (ts.get("StazioniFerme") or []):
        add(s)
    for s in (ts.get("StazioniNonFerme") or []):
        add(s)

    # sort by StationNumber if present
    def station_num(o: Dict[str, Any]) -> int:
        try:
            return int(o.get("StationNumber", 10**9))
        except Exception:
            return 10**9

    stops_raw.sort(key=station_num)

    # Extract estimated times
    arr_mins = [parse_hhmm(s.get("EstimatedArrivalTime")) for s in stops_raw]
    dep_mins = [parse_hhmm(s.get("EstimatedDepartureTime")) for s in stops_raw]

    # Apply rollover inference separately for arr/dep
    arr_mins2 = infer_rollover_minutes(arr_mins)
    dep_mins2 = infer_rollover_minutes(dep_mins)

    # Ensure per-stop consistency: if both times exist and departure < arrival, assume it rolled over
    for i in range(len(stops_raw)):
        a = arr_mins2[i]
        d = dep_mins2[i]
        if a is not None and d is not None and d < a:
            dep_mins2[i] = d + 1440

    stops: List[Dict[str, Any]] = []
    for i, s in enumerate(stops_raw):
        seq = station_num(s)
        name = s.get("LocationDescription")
        code = s.get("LocationCode")
        rfi = s.get("RfiLocationCode")

        arr_out = fmt_gtfs_time(arr_mins2[i])
        dep_out = fmt_gtfs_time(dep_mins2[i])

        # --- sanitize endpoints ---
        # First stop: arrival is not meaningful in these payloads (often "01:00")
        if i == 0:
            arr_out = None

        # Last stop: departure is not meaningful in these payloads (often "01:00")
        if i == len(stops_raw) - 1:
            dep_out = None

        stops.append({
            "stop_sequence": seq if seq != 10**9 else i,
            "stop_name": name,
            "location_code": code,
            "rfi_location_code": rfi,
            "arrival_time": arr_out,
            "departure_time": dep_out,
        })

    return {
        "train_number": train,
        "last_update": raw.get("LastUpdate"),
        "captured_utc": datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ"),
        "origin_station": ts.get("DepartureStationDescription"),
        "destination_station": ts.get("ArrivalStationDescription"),
        "origin_code": ts.get("DepartureStation"),
        "destination_code": ts.get("ArrivalStation"),
        "stops": stops,
    }


def main() -> None:
    ap = argparse.ArgumentParser(description="Normalize Italo italoinviaggio raw JSON to schedule JSON (estimated only).")
    ap.add_argument("--input-dir", required=True, help="Directory containing raw train JSON files (e.g., out/<run>/)")
    ap.add_argument("--output-dir", required=True, help="Directory to write normalized JSON (e.g., normalized/<run>/)")
    args = ap.parse_args()

    in_dir = args.input_dir
    out_dir = args.output_dir
    os.makedirs(out_dir, exist_ok=True)

    stats = {"normalized": 0, "skipped_empty": 0, "skipped_nonjson": 0, "errors": 0}

    for fname in os.listdir(in_dir):
        if not fname.endswith(".json"):
            continue
        if fname == "_summary.json":
            continue

        train = fname.replace(".json", "")
        in_path = os.path.join(in_dir, fname)
        out_path = os.path.join(out_dir, f"{train}.normalized.json")

        try:
            raw = load_json(in_path)
            normalized = extract_stops_from_train_schedule(raw, train)
            if not normalized:
                stats["skipped_empty"] += 1
                continue
            write_json(out_path, normalized)
            stats["normalized"] += 1
        except json.JSONDecodeError:
            stats["skipped_nonjson"] += 1
        except Exception as e:
            stats["errors"] += 1
            # optional: write an error marker
            err_path = os.path.join(out_dir, f"{train}.error.json")
            write_json(err_path, {"train": train, "error": str(e)})

    write_json(os.path.join(out_dir, "_summary.json"), stats)
    print(stats)


if __name__ == "__main__":
    main()