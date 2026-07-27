Here is a clean, minimal, accurate README for your current setup (cumulative GTFS, 8-day window, local rebuild script, manual coordinates).

You can paste this into README.md.

⸻

Italo Train Scraper → GTFS Builder

This repository:
	1.	Scrapes Italo train schedules from
https://italoinviaggio.italotreno.com/api/RicercaTrenoService
	2.	Normalizes them into a stable intermediate format
	3.	Builds a cumulative GTFS feed
	4.	Publishes:
	•	A stable GTFS URL
	•	Stop coordinate reports
	•	Collection status metadata

⸻

🌍 Public URLs

Base:

https://alvarotrabanco.github.io/italo-train-scraper/

Stable GTFS:

/gtfs/italo_latest.zip

Latest dated GTFS:

/gtfs/italo_YYYYMMDD.zip

Stop coordinate report:

/reports/stops_report_latest.csv

Collection status:

/state/collection_status.json


⸻

🧠 System Logic

GitHub Actions (Hourly)

Workflow: .github/workflows/publish_gtfs.yml

Every hour:
	1.	Checks 8-day collection window.
	2.	Restores cumulative normalized state from gh-pages/state/normalized_latest.
	3.	Scrapes trains from scraper/trains.txt.
	4.	Normalizes new data.
	5.	Merges into cumulative normalized_latest.
	6.	Builds GTFS from cumulative dataset.
	7.	Generates stop coordinate report.
	8.	Publishes everything to gh-pages.

The GTFS grows more complete over the 8-day window.

After 8 days, the workflow stops scraping but keeps publishing status.

⸻

📂 Important Folders

Folder	Purpose
scraper/	All Python scripts
normalized/	Per-run normalized output
normalized_latest/	Cumulative normalized set (local only)
coordinates.csv	Manual stop coordinates
public/	Published to GitHub Pages
state/	Persisted cumulative state from gh-pages


⸻

🧩 Scripts Overview

scraper/italo_scrape.py

Scrapes raw JSON per train number.

scraper/normalize_italo.py

Extracts scheduled stops and times.

scraper/build_gtfs.py

Builds GTFS zip from normalized JSON + coordinates.csv.

scraper/report_stops.py

Generates:
	•	stops_report_latest.csv
	•	stops_report_latest.md
	•	stop_inventory.json

scraper/make_normalized_latest.py

Merges all local normalized runs into normalized_latest/.

scraper/rebuild_reports.sh

One-command local rebuild of reports from GitHub cumulative state.

⸻

🛠 Local Workflow (Manual Coordinates Loop)

1️⃣ Rebuild local reports from cumulative state

From repo root:

./scraper/rebuild_reports.sh

This:
	•	fetches gh-pages
	•	restores state/normalized_latest
	•	rebuilds normalized_latest
	•	regenerates reports/stops_report_latest.csv

⸻

2️⃣ Check missing coordinates

Open:

reports/stops_report_latest.csv

Filter by:
	•	MISSING_COORDINATES
	•	NEW_NOT_IN_COORDINATES

These are the stops that need lat/lon.

⸻

3️⃣ Edit coordinates

File:

coordinates.csv

Format:

location_name,lat,lon

Example:

Agropoli Castellabate,40.351234,14.998765

Names must match exactly the stop names in normalized JSON.

⸻

4️⃣ Commit and push

git add coordinates.csv
git commit -m "Update Italo stop coordinates"
git push

Next GitHub Actions run will:
	•	rebuild GTFS
	•	update stop report
	•	publish updated feed

⸻

🔁 Optional: Build GTFS locally

python3 scraper/make_normalized_latest.py

python3 scraper/build_gtfs.py \
  --normalized-dir normalized_latest \
  --service-date $(date -u -d 'tomorrow' +%Y%m%d) \
  --out-zip gtfs/local_test.zip


⸻

📊 How to Verify Cumulative Collection

Open:

/gtfs/latest.json

Key fields:
	•	normalized_latest_files
	•	gtfs_trips

These should increase (or remain stable) over time.

⸻

⚠️ Important Notes
	•	Coordinates are matched by stop_name (exact string match).
	•	If a stop appears in GTFS but not in report, regenerate local report from cumulative state.
	•	--skip-empty in scraper means only active trains are captured at runtime.

⸻

🧹 8-Day Collection Window

The workflow automatically stops scraping after 8 days.

Status is visible at:

/state/collection_status.json
