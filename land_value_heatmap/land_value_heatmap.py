import os

import geopandas as gpd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
from matplotlib.cm import ScalarMappable
from matplotlib.colors import Normalize
import contextily as cx

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
CHARTS_DIR = os.path.join(SCRIPT_DIR, "charts")
os.makedirs(CHARTS_DIR, exist_ok=True)

print("Loading GeoJSON...")
gdf_full = gpd.read_file(os.path.join(SCRIPT_DIR, "..", "Tax_Parcels.geojson"), engine="pyogrio")

# Aggregate residential unit land values to master parcel level
res = gdf_full[gdf_full["PropertyClass"] == "Residential"].copy()
agg = res.groupby("XRefParcel", as_index=False).agg(
    CurrentLand=("CurrentLand", "sum"),
    PreviousLand=("PreviousLand", "sum"),
    PreviousLand2=("PreviousLand2", "sum"),
)

# Join geometry + LotSize from the master parcel row
master = gdf_full[["Parcel", "LotSize", "geometry"]].rename(columns={"Parcel": "XRefParcel"})
merged = agg.merge(master, on="XRefParcel", how="left")
merged = gpd.GeoDataFrame(merged, geometry="geometry")

# % change in land value (condo-aggregated)
merged["land_pct"] = np.where(
    merged["PreviousLand"] != 0,
    (merged["CurrentLand"] - merged["PreviousLand"]) / merged["PreviousLand"] * 100.0,
    np.nan,
)

# Absolute dollar change per sqft
merged["land_delta_sqft"] = np.where(
    merged["LotSize"] > 0,
    (merged["CurrentLand"] - merged["PreviousLand"]) / merged["LotSize"],
    np.nan,
)

# Current (2026) land value per sqft
merged["land_sqft_2026"] = np.where(
    merged["LotSize"] > 0,
    merged["CurrentLand"] / merged["LotSize"],
    np.nan,
)

# Previous (2025) land value per sqft
merged["land_sqft_2025"] = np.where(
    merged["LotSize"] > 0,
    merged["PreviousLand"] / merged["LotSize"],
    np.nan,
)

# Previous2 (2024) land value per sqft
merged["land_sqft_2024"] = np.where(
    merged["LotSize"] > 0,
    merged["PreviousLand2"] / merged["LotSize"],
    np.nan,
)

merged = merged.set_crs("EPSG:4326").to_crs(epsg=3857)
print(f"Mapped parcels (condo-grouped): {len(merged):,}")


def plot_heatmap(gdf, column, cmap, vmin, vmax, title, subtitle, cbar_label, cbar_fmt, outfile):
    print(f"  Color range: {vmin:.3g} to {vmax:.3g}")
    fig, ax = plt.subplots(figsize=(12, 10))
    fig.suptitle(title, fontsize=16, fontweight="bold")
    ax.set_title(subtitle, fontsize=11, color="#555555", pad=8)
    gdf.plot(
        column=column, cmap=cmap, vmin=vmin, vmax=vmax,
        linewidth=0, ax=ax, legend=False, missing_kwds={"color": "lightgrey"},
    )
    cx.add_basemap(ax, crs=gdf.crs, source=cx.providers.CartoDB.Positron)
    norm = Normalize(vmin=vmin, vmax=vmax)
    sm = ScalarMappable(cmap=cmap, norm=norm)
    sm.set_array([])
    cbar = fig.colorbar(sm, ax=ax, orientation="horizontal", shrink=0.5, pad=0.02)
    cbar.set_label(cbar_label, fontsize=10)
    cbar.ax.xaxis.set_major_formatter(cbar_fmt)
    ax.set_axis_off()
    fig.tight_layout()
    outpath = os.path.join(CHARTS_DIR, outfile)
    fig.savefig(outpath, dpi=150, bbox_inches="tight")
    print(f"Saved {outpath}")


# Figure 1: % change in land value
q1, q3 = merged["land_pct"].quantile(0.25), merged["land_pct"].quantile(0.75)
iqr = q3 - q1
plot_heatmap(
    merged, "land_pct", "Blues", q1 - 1.5 * iqr, q3 + 1.5 * iqr,
    title="Residential Land Value % Change",
    subtitle="Current vs. Previous Assessment  |  Color range: 1.5×IQR  |  Condos grouped to master parcel",
    cbar_label="Land Value % Change",
    cbar_fmt=mticker.FuncFormatter(lambda v, _: f"{v:+.0f}%"),
    outfile="land_value_heatmap.png",
)

# Figure 2: absolute dollar change per sqft
q1, q3 = merged["land_delta_sqft"].quantile(0.25), merged["land_delta_sqft"].quantile(0.75)
iqr = q3 - q1
plot_heatmap(
    merged, "land_delta_sqft", "Blues", q1 - 1.5 * iqr, q3 + 1.5 * iqr,
    title="Residential Land Value Change per Sq Ft",
    subtitle="(CurrentLand − PreviousLand) / LotSize  |  Color range: 1.5×IQR  |  Condos grouped to master parcel",
    cbar_label="Land Value Change ($/sqft)",
    cbar_fmt=mticker.FuncFormatter(lambda v, _: f"${v:+.2f}"),
    outfile="land_value_sqft_heatmap.png",
)

# Figures 3 & 4: 2026 and 2025 land value per sqft — shared color bounds for comparability
q1, q3 = merged["land_sqft_2026"].quantile(0.25), merged["land_sqft_2026"].quantile(0.75)
iqr = q3 - q1
sqft_vmin, sqft_vmax = 0, q3 + 1.5 * iqr

plot_heatmap(
    merged, "land_sqft_2024", "magma_r", sqft_vmin, sqft_vmax,
    title="Residential Land Value per Sq Ft (2024)",
    subtitle="PreviousLand2 / LotSize  |  Color range: 1.5×IQR from 2026  |  Condos grouped to master parcel",
    cbar_label="Land Value ($/sqft)",
    cbar_fmt=mticker.FuncFormatter(lambda v, _: f"${v:,.0f}"),
    outfile="land_value_sqft_2024_heatmap.png",
)

plot_heatmap(
    merged, "land_sqft_2026", "magma_r", sqft_vmin, sqft_vmax,
    title="Residential Land Value per Sq Ft (2026)",
    subtitle="CurrentLand / LotSize  |  Color range: 1.5×IQR from 2026  |  Condos grouped to master parcel",
    cbar_label="Land Value ($/sqft)",
    cbar_fmt=mticker.FuncFormatter(lambda v, _: f"${v:,.0f}"),
    outfile="land_value_sqft_2026_heatmap.png",
)

plot_heatmap(
    merged, "land_sqft_2025", "magma_r", sqft_vmin, sqft_vmax,
    title="Residential Land Value per Sq Ft (2025)",
    subtitle="PreviousLand / LotSize  |  Color range: 1.5×IQR from 2026  |  Condos grouped to master parcel",
    cbar_label="Land Value ($/sqft)",
    cbar_fmt=mticker.FuncFormatter(lambda v, _: f"${v:,.0f}"),
    outfile="land_value_sqft_2025_heatmap.png",
)

from PIL import Image, ImageDraw, ImageFont


def annotate_year(img, year):
    img = img.copy().convert("RGBA")
    draw = ImageDraw.Draw(img)
    text = str(year)
    try:
        font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", size=96)
    except OSError:
        font = ImageFont.load_default()
    x, y = 30, 160
    bbox = draw.textbbox((x, y), text, font=font)
    pad = 8
    draw.rectangle(
        [bbox[0] - pad, bbox[1] - pad, bbox[2] + pad, bbox[3] + pad],
        fill=(0, 0, 0, 160),
    )
    draw.text((x, y), text, font=font, fill=(255, 255, 255, 255))
    return img.convert("RGB")


frames_2yr = [
    annotate_year(Image.open(os.path.join(CHARTS_DIR, "land_value_sqft_2025_heatmap.png")), 2025),
    annotate_year(Image.open(os.path.join(CHARTS_DIR, "land_value_sqft_2026_heatmap.png")), 2026),
]
frames_2yr[0].save(
    os.path.join(CHARTS_DIR, "land_value_sqft_comparison.webp"),
    save_all=True,
    append_images=frames_2yr[1:],
    duration=2000,
    loop=0,
)
print("Saved land_value_sqft_comparison.webp")

frames_3yr = [
    annotate_year(Image.open(os.path.join(CHARTS_DIR, "land_value_sqft_2024_heatmap.png")), 2024),
    annotate_year(Image.open(os.path.join(CHARTS_DIR, "land_value_sqft_2025_heatmap.png")), 2025),
    annotate_year(Image.open(os.path.join(CHARTS_DIR, "land_value_sqft_2026_heatmap.png")), 2026),
]
frames_3yr[0].save(
    os.path.join(CHARTS_DIR, "land_value_sqft_3yr_comparison.webp"),
    save_all=True,
    append_images=frames_3yr[1:],
    duration=[1000, 1000, 2000],
    loop=0,
)
print("Saved land_value_sqft_3yr_comparison.webp")
print("Done.")
