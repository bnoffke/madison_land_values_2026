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
COLORS = {"land": "#6AAB6A", "improvement": "#5B8DB8", "total": "#9B6BAE"}
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
plt.close(fig)
print("Saved gorham_trend.png")

# ---------------------------------------------------------------------------
# Step 5: Four alternative chart variants (mobile-optimised)
# ---------------------------------------------------------------------------
COLOR_117 = "#6AAB6A"   # green — 117 land (Improved)
COLOR_113 = "#a8d9a8"   # lighter green — 113 land (Vacant)
COLOR_IMPR = "#5B8DB8"  # blue — improvement
COLOR_TOTAL = "#9B6BAE" # purple — total
COLOR_GAP = "#d62728"   # red — underassessed gap


def add_markers(ax, df_p, series, color):
    hm = df_p["year"] < 2026
    pm = df_p["year"] == 2026
    ax.plot(df_p.loc[hm, "year"], df_p.loc[hm, series], "o", color=color, markersize=5, zorder=5)
    ax.plot(df_p.loc[pm, "year"], df_p.loc[pm, series], "*", color=color, markersize=12, zorder=6)


def style_ax(ax, yr_list):
    ax.set_xlabel("Year", fontsize=10)
    ax.set_ylabel("Assessed Value", fontsize=10)
    ax.set_xticks(yr_list)
    ax.tick_params(axis="x", rotation=45)
    ax.yaxis.set_major_formatter(dollar_fmt)
    ax.grid(axis="y", alpha=0.4)
    ax.set_axisbelow(True)


yrs = df_117["year"].tolist()
land_117_2026 = float(df_117.loc[df_117["year"] == 2026, "land"].iloc[0])
land_113_2026 = float(df_113.loc[df_113["year"] == 2026, "land"].iloc[0])

# ── V1: Single overlay panel ─────────────────────────────────────────────────
fig, ax = plt.subplots(figsize=(6, 7))
fig.suptitle("117 vs. 113 W Gorham: Assessed Values", fontsize=13, fontweight="bold")

ax.plot(yrs, df_117["land"], color=COLOR_117, linewidth=2, label="Land — 117 W Gorham (Improved)")
add_markers(ax, df_117, "land", COLOR_117)
ax.plot(yrs, df_113["land"], color=COLOR_113, linewidth=2, linestyle="--", label="Land — 113 W Gorham (Vacant)")
add_markers(ax, df_113, "land", COLOR_113)
ax.fill_between(yrs, df_117["land"], df_117["total"], color=COLOR_IMPR, alpha=0.25,
                label="Improvement — 117 W Gorham")
ax.plot(yrs, df_117["total"], color=COLOR_TOTAL, linewidth=1.5, linestyle=":", label="Total — 117 W Gorham")
add_markers(ax, df_117, "total", COLOR_TOTAL)

style_ax(ax, yrs)
ax.legend(loc="upper left", fontsize=9)
fig.tight_layout()
fig.savefig(os.path.join(CHARTS_DIR, "gorham_trend_v1_overlay.png"), dpi=150, bbox_inches="tight")
plt.close(fig)
print("Saved gorham_trend_v1_overlay.png")

# ── V2: Vertical stack 2×1, independent Y-axes ───────────────────────────────
fig, (ax_top, ax_bot) = plt.subplots(2, 1, figsize=(6, 10))
fig.suptitle("Assessed Value Trends: 117 vs. 113 W Gorham St", fontsize=13, fontweight="bold")

plot_parcel(ax_top, df_117, "117 W Gorham — Improved (3-Unit Residential)")
plot_parcel(ax_bot, df_113, "113 W Gorham — Vacant Land (Residential Parking)", series_list=("land",))
ax_top.set_ylabel("Assessed Value", fontsize=10)
ax_bot.set_ylabel("Assessed Value", fontsize=10)

ax_top.annotate(
    f"2026 Land:\n${land_117_2026:,.0f}",
    xy=(2026, land_117_2026), xytext=(2022, land_117_2026 * 1.05),
    arrowprops=dict(arrowstyle="->", color=COLOR_117, lw=1.5),
    fontsize=9, color=COLOR_117, ha="right",
)
ax_bot.annotate(
    f"2026 Land:\n${land_113_2026:,.0f}\n(≈ 117 land)",
    xy=(2026, land_113_2026), xytext=(2022, land_113_2026 * 0.95),
    arrowprops=dict(arrowstyle="->", color=COLOR_113, lw=1.5),
    fontsize=9, color=COLOR_113, ha="right",
)

handles_top, labels_top = ax_top.get_legend_handles_labels()
fig.legend(handles_top, labels_top, loc="lower center", ncol=3, fontsize=9,
           bbox_to_anchor=(0.5, -0.02))
fig.tight_layout()
fig.savefig(os.path.join(CHARTS_DIR, "gorham_trend_v2_vstack.png"), dpi=150, bbox_inches="tight")
plt.close(fig)
print("Saved gorham_trend_v2_vstack.png")

# ── V3: Grouped bar chart ─────────────────────────────────────────────────────
x = df_117["year"].values
bar_w = 0.35

fig, ax = plt.subplots(figsize=(10, 6))
fig.suptitle("Assessed Values by Year: 117 vs. 113 W Gorham St", fontsize=13, fontweight="bold")

ax.bar(x - bar_w / 2, df_117["land"], bar_w, color=COLOR_117, label="Land — 117 W Gorham (Improved)", zorder=3)
ax.bar(x - bar_w / 2, df_117["improvement"], bar_w, bottom=df_117["land"],
       color=COLOR_IMPR, label="Improvement — 117 W Gorham", zorder=3)
ax.bar(x + bar_w / 2, df_113["land"], bar_w, color=COLOR_113, hatch="//",
       edgecolor="#3a8a3a", linewidth=0.8, label="Land — 113 W Gorham (Vacant)", zorder=3)

ax.set_xlabel("Year", fontsize=10)
ax.set_ylabel("Assessed Value", fontsize=10)
ax.set_xticks(x)
ax.set_xticklabels([str(y) for y in yrs], rotation=45)
ax.yaxis.set_major_formatter(dollar_fmt)
ax.grid(axis="y", alpha=0.4)
ax.set_axisbelow(True)
ax.legend(loc="upper left", fontsize=9)
fig.tight_layout()
fig.savefig(os.path.join(CHARTS_DIR, "gorham_trend_v3_bar.png"), dpi=150, bbox_inches="tight")
plt.close(fig)
print("Saved gorham_trend_v3_bar.png")

# ── V4: Gap / divergence chart ────────────────────────────────────────────────
merged = (
    df_117[["year", "land", "improvement", "total"]]
    .rename(columns={"land": "land_117", "improvement": "impr_117", "total": "total_117"})
    .merge(df_113[["year", "land"]].rename(columns={"land": "land_113"}), on="year")
    .sort_values("year")
    .reset_index(drop=True)
)
yrs_m = merged["year"].tolist()

fig, ax = plt.subplots(figsize=(6, 7))
fig.suptitle("Land Value Gap: 117 vs. 113 W Gorham St", fontsize=13, fontweight="bold")

ax.fill_between(yrs_m, merged["land_113"], merged["land_117"],
                color=COLOR_GAP, alpha=0.25, label="Underassessed Land Gap")
ax.plot(yrs_m, merged["land_117"], color=COLOR_117, linewidth=2, label="Land — 117 W Gorham (Improved)")
add_markers(ax, df_117, "land", COLOR_117)
ax.plot(yrs_m, merged["land_113"], color=COLOR_113, linewidth=2, linestyle="--",
        label="Land — 113 W Gorham (Vacant)")
add_markers(ax, df_113, "land", COLOR_113)

gap_mid_2026 = (land_117_2026 + land_113_2026) / 2
ax.annotate(
    "Gap\ncloses →",
    xy=(2026, gap_mid_2026), xytext=(2022.5, gap_mid_2026),
    arrowprops=dict(arrowstyle="->", color=COLOR_GAP, lw=1.5),
    color=COLOR_GAP, fontsize=9, ha="right",
)

style_ax(ax, yrs_m)
ax.legend(loc="upper left", fontsize=9)
fig.tight_layout()
fig.savefig(os.path.join(CHARTS_DIR, "gorham_trend_v4_gap.png"), dpi=150, bbox_inches="tight")
plt.close(fig)
print("Saved gorham_trend_v4_gap.png")
