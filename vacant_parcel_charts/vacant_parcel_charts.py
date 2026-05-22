import geopandas as gpd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import contextily as cx

print("Loading GeoJSON...")
gdf = gpd.read_file("Tax_Parcels.geojson", engine="pyogrio")

res = gdf[gdf["PropertyClass"] == "Residential"].copy()
vacant  = res[res["PropertyUse"].str.contains("vacant", case=False, na=False)].copy()
improved = res[~res["PropertyUse"].str.contains("vacant", case=False, na=False)].copy()

print(f"Residential parcels: {len(res):,}  |  Vacant: {len(vacant):,}  |  Improved: {len(improved):,}")

# Fill LotSize == 0 from geometry-derived area for vacant parcels only (sq meters → sq ft)
vacant   = res[res["PropertyUse"].str.contains("vacant", case=False, na=False)].copy()
improved = res[~res["PropertyUse"].str.contains("vacant", case=False, na=False)].copy()

zero_mask = vacant["LotSize"] == 0
if zero_mask.any():
    projected = vacant[zero_mask].set_crs("EPSG:4326").to_crs(epsg=3857)
    vacant.loc[zero_mask, "LotSize"] = projected.geometry.area * 10.7639
    print(f"Filled {zero_mask.sum()} zero-LotSize vacant parcels from geometry")

# ---------------------------------------------------------------------------
# Figure 1: Lot size distribution — vacant vs. improved (reference)
# ---------------------------------------------------------------------------
lot_cap = 50000
v_lots = vacant[vacant["LotSize"] <= lot_cap]["LotSize"].dropna()

bin_edges = np.linspace(0, lot_cap, 60)

fig1, ax1 = plt.subplots(figsize=(10, 6))
fig1.suptitle("Vacant Residential Parcel — Lot Size Distribution", fontsize=16, fontweight="bold")
ax1.set_title(
    f"Madison, WI  |  n={len(v_lots):,} of 1,417 vacant parcels  |  Showing ≤ {lot_cap:,.0f} sq ft",
    fontsize=11, color="#555555", pad=8,
)

ax1.hist(v_lots, bins=bin_edges, color="#E07B4C", alpha=0.85, zorder=2)

v_med = v_lots.median()
ax1.axvline(v_med, color="#333333", linewidth=2, linestyle="--", zorder=3)
ax1.text(v_med + lot_cap * 0.01, ax1.get_ylim()[1] * 0.95,
         f"Median\n{v_med:,.0f} sq ft",
         color="#333333", fontsize=10, va="top")

ax1.set_xlabel("Lot Size (sq ft)", fontsize=12)
ax1.set_ylabel("Number of Parcels", fontsize=12)
ax1.xaxis.set_major_formatter(mticker.FuncFormatter(lambda v, _: f"{v:,.0f}"))
ax1.grid(axis="y", color="#dddddd", zorder=1)
ax1.set_axisbelow(True)
ax1.spines[["top", "right"]].set_visible(False)

fig1.tight_layout()
fig1.savefig("vacant_lot_size_distribution.png", dpi=150, bbox_inches="tight")
print("Saved vacant_lot_size_distribution.png")

# ---------------------------------------------------------------------------
# Figure 2: Map of vacant residential parcels
# ---------------------------------------------------------------------------
vacant_geo  = vacant.set_crs("EPSG:4326").to_crs(epsg=3857)
improved_geo = improved.set_crs("EPSG:4326").to_crs(epsg=3857)

fig2, ax2 = plt.subplots(figsize=(12, 10))
fig2.suptitle("Vacant Residential Parcels in Madison, WI", fontsize=16, fontweight="bold")
ax2.set_title(
    f"{len(vacant_geo):,} vacant parcels (2.0% of residential tax base)  |  2026 Assessment",
    fontsize=11, color="#555555", pad=8,
)

improved_geo.plot(ax=ax2, color="#cccccc", linewidth=0, alpha=0.5, zorder=2)
vacant_geo.plot(ax=ax2, color="#E07B4C", linewidth=0.3, edgecolor="#c05a2a", alpha=0.85, zorder=3)

cx.add_basemap(ax2, crs=vacant_geo.crs, source=cx.providers.CartoDB.Positron)

from matplotlib.lines import Line2D
legend_handles = [
    Line2D([0], [0], marker="s", color="w", markerfacecolor="#cccccc", markersize=12, alpha=0.5, label="Improved residential"),
    Line2D([0], [0], marker="s", color="w", markerfacecolor="#E07B4C", markersize=12, label="Vacant residential"),
]
ax2.legend(handles=legend_handles, loc="lower right", fontsize=11, framealpha=0.9)
ax2.set_axis_off()

fig2.tight_layout()
fig2.savefig("vacant_parcel_map.png", dpi=150, bbox_inches="tight")
print("Saved vacant_parcel_map.png")

plt.show()
print("Done.")
