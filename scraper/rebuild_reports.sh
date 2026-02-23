#!/usr/bin/env bash
set -euo pipefail

# Run from anywhere; anchor to repo root
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

WINDOW_HOURS="${WINDOW_HOURS:-192}"

echo "[1/6] Fetch gh-pages..."
git fetch origin gh-pages

echo "[2/6] Restore persisted state files (if they exist)..."
mkdir -p state reports
git checkout origin/gh-pages -- state/normalized_latest reports/stop_inventory.json 2>/dev/null || true

echo "[3/6] Rebuild normalized_latest/ from persisted state..."
rm -rf normalized_latest
mkdir -p normalized_latest
cp -f state/normalized_latest/*.normalized.json normalized_latest/ 2>/dev/null || true

NORM_COUNT="$(ls -1 normalized_latest 2>/dev/null | wc -l | tr -d ' ')"
if [ "${NORM_COUNT}" -eq 0 ]; then
  echo "ERROR: normalized_latest is empty."
  echo "This usually means gh-pages doesn't have state/normalized_latest yet (or you haven't had a successful publish run)."
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