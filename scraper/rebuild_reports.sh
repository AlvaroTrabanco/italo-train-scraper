#!/usr/bin/env bash
set -euo pipefail

# Run from anywhere; anchor to repo root
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

WINDOW_HOURS="${WINDOW_HOURS:-192}"
LIVE_BASE="${LIVE_BASE:-https://italotrainscraper.netlify.app}"

echo "[1/6] Restore persisted state files from live Netlify site..."
mkdir -p state/normalized_latest reports normalized_latest

# Download latest stop inventory
curl -fsSL "$LIVE_BASE/reports/stop_inventory.json" -o reports/stop_inventory.json

# Download manifest of normalized_latest files
curl -fsSL "$LIVE_BASE/state/normalized_latest_manifest.txt" -o state/normalized_latest_manifest.txt

echo "[2/6] Refresh local normalized state from live manifest..."
rm -f state/normalized_latest/*.normalized.json 2>/dev/null || true
rm -f normalized_latest/*.normalized.json 2>/dev/null || true

while IFS= read -r fn; do
  [ -n "$fn" ] || continue
  echo "  - $fn"
  curl -fsSL "$LIVE_BASE/state/normalized_latest/$fn" -o "state/normalized_latest/$fn"
done < state/normalized_latest_manifest.txt

echo "[3/6] Rebuild normalized_latest/ from persisted state..."
cp -f state/normalized_latest/*.normalized.json normalized_latest/ 2>/dev/null || true

NORM_COUNT="$(ls -1 normalized_latest 2>/dev/null | wc -l | tr -d ' ')"
if [ "${NORM_COUNT}" -eq 0 ]; then
  echo "ERROR: normalized_latest is empty."
  echo "This usually means the live site doesn't have state/normalized_latest yet or the manifest is missing."
  exit 1
fi
echo "normalized_latest files: ${NORM_COUNT}"

echo "[4/6] Build stops report (latest) into reports/ ..."
RUN_UTC="local_$(date -u +%Y%m%dT%H%M%SZ)"

python3 scraper/report_stops.py \
  --normalized-dir normalized_latest \
  --coordinates coordinates.csv \
  --out-dir reports \
  --run-utc "$RUN_UTC" \
  --inventory-in reports/stop_inventory.json \
  --inventory-out reports/stop_inventory.json \
  --window-hours "$WINDOW_HOURS"

echo "[5/6] Done."
echo " - reports/stops_report_latest.csv"
echo " - reports/stops_report_latest.md"
echo " - reports/stop_inventory.json (updated)"
echo ""
echo "[6/6] Next steps:"
echo "  1) Edit coordinates.csv"
echo "  2) git add coordinates.csv"
echo "  3) git commit -m \"Add Italo stop coordinates\""
echo "  4) git push"