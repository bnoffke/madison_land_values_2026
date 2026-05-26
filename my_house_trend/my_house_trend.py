import json
import os
import re
import subprocess

import geopandas as gpd
import matplotlib.pyplot as plt
import pandas as pd

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
CHARTS_DIR = os.path.join(SCRIPT_DIR, "charts")
os.makedirs(CHARTS_DIR, exist_ok=True)

PARCEL_ID = "070929101015"

# ---------------------------------------------------------------------------
# Query 2016–2025 from parquet
# ---------------------------------------------------------------------------
SQL = f"""
SELECT tax_year, assessed_value_land, assessed_value_improvement, total_assessed_value
FROM read_parquet('gs://stmsn-silver/fact_tax_roll.parquet')
WHERE parcel_id = '{PARCEL_ID}'
ORDER BY tax_year
"""
result = subprocess.run(["duckquery", SQL.strip()], capture_output=True, text=True, check=True)
json_text = re.search(r"\[.*\]", result.stdout, re.DOTALL).group()
hist = pd.DataFrame(json.loads(json_text))
hist.columns = ["year", "land", "improvement", "total"]

# ---------------------------------------------------------------------------
# Load 2026 from GeoJSON
# ---------------------------------------------------------------------------
gdf = gpd.read_file(os.path.join(SCRIPT_DIR, "..", "Tax_Parcels.geojson"), engine="pyogrio")
row = gdf[gdf["Parcel"] == PARCEL_ID].iloc[0]
df_2026 = pd.DataFrame([{
    "year": 2026,
    "land": float(row["CurrentLand"]),
    "improvement": float(row["CurrentImpr"]),
    "total": float(row["CurrentTotal"]),
}])

df = pd.concat([hist, df_2026], ignore_index=True)

# ---------------------------------------------------------------------------
# Plot
# ---------------------------------------------------------------------------
COLORS = {"land": "#6AAB6A", "improvement": "#5B8DB8", "total": "#9B6BAE"}
LABELS = {"land": "Land Value", "improvement": "Improvement Value", "total": "Total Value"}

fig, ax = plt.subplots(figsize=(6, 7))
fig.suptitle("My House", fontsize=14, fontweight="bold")

years = df["year"].tolist()
hist_mask = df["year"] < 2026
proj_mask = df["year"] == 2026

for series in ("land", "improvement", "total"):
    color = COLORS[series]
    ax.plot(years, df[series].tolist(), color=color, linewidth=2, label=LABELS[series])
    ax.plot(df.loc[hist_mask, "year"], df.loc[hist_mask, series], "o", color=color, markersize=5, zorder=5)
    ax.plot(df.loc[proj_mask, "year"], df.loc[proj_mask, series], "*", color=color, markersize=12, zorder=6)

ax.set_xticks(years)
ax.tick_params(axis="x", rotation=45)
ax.yaxis.set_major_locator(plt.MultipleLocator(150_000))
ax.yaxis.set_ticklabels([])
ax.tick_params(axis="y", left=False)
ax.set_ylabel("")
ax.grid(axis="y", alpha=0.4)
ax.set_axisbelow(True)
ax.legend(loc="upper left", fontsize=9)

fig.tight_layout()
fig.savefig(os.path.join(CHARTS_DIR, "my_house_trend.png"), dpi=150, bbox_inches="tight")
print("Saved my_house_trend.png")
