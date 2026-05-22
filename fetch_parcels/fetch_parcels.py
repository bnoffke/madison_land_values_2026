import json
import os
import time
import requests

BASE_URL = "https://maps.cityofmadison.com/arcgis/rest/services/Public/OPEN_DATA2/FeatureServer/0/query"
PAGE_SIZE = 1000
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_FILE = os.path.join(SCRIPT_DIR, "..", "Tax_Parcels.geojson")

def get_total_count():
    r = requests.get(BASE_URL, params={
        "where": "1=1",
        "returnCountOnly": "true",
        "f": "json",
    })
    r.raise_for_status()
    return r.json()["count"]

def fetch_page(offset):
    r = requests.get(BASE_URL, params={
        "outFields": "*",
        "where": "1=1",
        "resultOffset": offset,
        "resultRecordCount": PAGE_SIZE,
        "f": "geojson",
    })
    r.raise_for_status()
    return r.json()

total = get_total_count()
pages = (total + PAGE_SIZE - 1) // PAGE_SIZE
print(f"Total parcels: {total:,}  |  Pages: {pages}  |  Page size: {PAGE_SIZE}")

all_features = []
for i in range(pages):
    offset = i * PAGE_SIZE
    data = fetch_page(offset)
    features = data.get("features", [])
    all_features.extend(features)
    print(f"  Page {i+1}/{pages}  fetched {len(features)}  total so far: {len(all_features):,}", flush=True)
    # Be polite to the server
    time.sleep(0.1)

geojson = {
    "type": "FeatureCollection",
    "name": "Tax_Parcels",
    "features": all_features,
}

with open(OUTPUT_FILE, "w") as f:
    json.dump(geojson, f)

print(f"\nSaved {len(all_features):,} features to {OUTPUT_FILE}")
