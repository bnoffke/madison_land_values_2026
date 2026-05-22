import json
import os
import re
import subprocess

import geopandas as gpd
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import pandas as pd

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
CHARTS_DIR = os.path.join(SCRIPT_DIR, "charts")
os.makedirs(CHARTS_DIR, exist_ok=True)

# ---------------------------------------------------------------------------
# Step 1: Query 2016–2025 from parquet
# ---------------------------------------------------------------------------
SQL = """
SELECT parcel_id, tax_year, assessed_value_land, assessed_value_improvement, total_assessed_value
FROM read_parquet('gs://stmsn-silver/fact_tax_roll.parquet')
WHERE parcel_id IN ('070914422038', '070914422020')
ORDER BY parcel_id, tax_year
"""
result = subprocess.run(["duckquery", SQL.strip()], capture_output=True, text=True, check=True)
json_text = re.search(r"\[.*\]", result.stdout, re.DOTALL).group()
hist = pd.DataFrame(json.loads(json_text))
hist.columns = ["parcel_id", "year", "land", "improvement", "total"]

# ---------------------------------------------------------------------------
# Step 2: Load 2026 values from GeoJSON
# ---------------------------------------------------------------------------
print("Loading GeoJSON for 2026 values...")
gdf = gpd.read_file(os.path.join(SCRIPT_DIR, "..", "Tax_Parcels.geojson"), engine="pyogrio")

PARCELS = {
    "070914422038": "117 W Gorham",
    "070914422020": "113 W Gorham",
}

rows_2026 = []
for pid, addr in PARCELS.items():
    row = gdf[gdf["Parcel"] == pid].iloc[0]
    rows_2026.append({
        "parcel_id": pid,
        "year": 2026,
        "land": float(row["CurrentLand"]),
        "improvement": float(row["CurrentImpr"]),
        "total": float(row["CurrentTotal"]),
    })

df_2026 = pd.DataFrame(rows_2026)

# ---------------------------------------------------------------------------
# Step 3: Combine and split by parcel
# ---------------------------------------------------------------------------
df = pd.concat([hist, df_2026], ignore_index=True).sort_values(["parcel_id", "year"])

df_117 = df[df["parcel_id"] == "070914422038"].reset_index(drop=True)
df_113 = df[df["parcel_id"] == "070914422020"].reset_index(drop=True)

# ---------------------------------------------------------------------------
# Step 4: Plot
# ---------------------------------------------------------------------------
COLORS = {"land": "#2ca02c", "improvement": "#1f77b4", "total": "#ff7f0e"}
LABELS = {"land": "Land Value", "improvement": "Improvement Value", "total": "Total Value"}

dollar_fmt = mticker.FuncFormatter(lambda v, _: f"${v:,.0f}")


def plot_parcel(ax, df_parcel, title, series_list=("land", "improvement", "total")):
    years = df_parcel["year"].tolist()
    hist_mask = df_parcel["year"] < 2026
    proj_mask = df_parcel["year"] == 2026

    for series in series_list:
        color = COLORS[series]
        label = LABELS[series]
        vals = df_parcel[series].tolist()

        # Full line connecting all years
        ax.plot(years, vals, color=color, linewidth=2, label=label)

        # Round markers on historical points
        ax.plot(
            df_parcel.loc[hist_mask, "year"],
            df_parcel.loc[hist_mask, series],
            "o", color=color, markersize=5, zorder=5,
        )

        # Star marker on 2026
        ax.plot(
            df_parcel.loc[proj_mask, "year"],
            df_parcel.loc[proj_mask, series],
            "*", color=color, markersize=12, zorder=6,
        )

    ax.set_title(title, fontsize=12, fontweight="bold")
    ax.set_xlabel("Year", fontsize=10)
    ax.set_xticks(years)
    ax.tick_params(axis="x", rotation=45)
    ax.yaxis.set_major_formatter(dollar_fmt)
    ax.grid(axis="y", alpha=0.4)
    ax.set_axisbelow(True)


fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 6), sharey=True)
fig.suptitle("Assessed Value Trends: 117 vs. 113 W Gorham St", fontsize=14, fontweight="bold", y=1.01)

plot_parcel(ax1, df_117, "117 W Gorham — Improved (3-Unit Residential)")
plot_parcel(ax2, df_113, "113 W Gorham — Vacant Land (Residential Parking)", series_list=("land",))

ax1.set_ylabel("Assessed Value", fontsize=10)
ax2.set_ylabel("")

# Single shared legend below both plots
handles, labels = ax1.get_legend_handles_labels()
fig.legend(
    handles, labels,
    loc="lower center", ncol=3, fontsize=10,
    bbox_to_anchor=(0.5, -0.06),
)

fig.tight_layout()
fig.savefig(os.path.join(CHARTS_DIR, "gorham_trend.png"), dpi=150, bbox_inches="tight")
print("Saved gorham_trend.png")
