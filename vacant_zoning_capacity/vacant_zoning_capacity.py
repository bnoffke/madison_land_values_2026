import os

import geopandas as gpd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
CHARTS_DIR = os.path.join(SCRIPT_DIR, "charts")
os.makedirs(CHARTS_DIR, exist_ok=True)

print("Loading GeoJSON...")
gdf = gpd.read_file(os.path.join(SCRIPT_DIR, "..", "Tax_Parcels.geojson"), engine="pyogrio")

vacant = gdf[
    (gdf["PropertyClass"] == "Residential") &
    gdf["PropertyUse"].str.contains("vacant", case=False, na=False)
].copy()

zero_mask = vacant["LotSize"] == 0
if zero_mask.any():
    proj = vacant[zero_mask].set_crs("EPSG:4326").to_crs(epsg=3857)
    vacant.loc[zero_mask, "LotSize"] = proj.geometry.area * 10.7639
    print(f"Filled {zero_mask.sum()} zero-LotSize parcels from geometry")

ZONE_RULES = {
    "SR-C1": {"min_lot": 6000, "coverage": 0.50},
    "SR-C2": {"min_lot": 5000, "coverage": 0.50},
    "SR-C3": {"min_lot": 4500, "coverage": 0.50},
    "TR-C1": {"min_lot": 5000, "coverage": 0.50},
    "TR-C2": {"min_lot": 4000, "coverage": 0.60},
    "TR-C3": {"min_lot": 3000, "coverage": 0.65},
    "TR-C4": {"min_lot": 3000, "coverage": 0.65},
    "TR-P":  {"min_lot": 2900, "coverage": 0.75},
}

# Extract base zone from ZoningAll (may contain overlays like "WP-26, SR-C1")
def extract_base_zone(zoning_all, known_zones):
    if not isinstance(zoning_all, str):
        return None
    for part in zoning_all.split(","):
        z = part.strip()
        if z in known_zones:
            return z
    return zoning_all.split(",")[0].strip()  # fall back to first token

vacant["zone"]     = vacant["ZoningAll"].apply(lambda v: extract_base_zone(v, set(ZONE_RULES)))
vacant["min_lot"]  = vacant["zone"].map({z: r["min_lot"]  for z, r in ZONE_RULES.items()})
vacant["coverage"] = vacant["zone"].map({z: r["coverage"] for z, r in ZONE_RULES.items()})
vacant["mapped"]   = vacant["min_lot"].notna()
vacant["buildable"] = vacant["mapped"] & (vacant["LotSize"] >= vacant["min_lot"])
vacant["units"] = np.where(
    ~vacant["mapped"],   np.nan,
    np.where(~vacant["buildable"], 0,
    np.where(vacant["LotSize"] >= 6000, 4, 2))
)

# ---------------------------------------------------------------------------
# Summary table
# ---------------------------------------------------------------------------
print(f"\n{'Zone':<8} {'Total':>6} {'Buildable':>10} {'Not Bldbl':>10} {'4-unit':>7} {'2-unit':>7} {'Pot. Units':>11}")
print("-" * 65)

zone_order = ["TR-P", "TR-C3", "TR-C4", "TR-C2", "TR-C1", "SR-C3", "SR-C2", "SR-C1"]
total_units = 0
for zone in zone_order:
    sub = vacant[vacant["zone"] == zone]
    n       = len(sub)
    bld     = sub["buildable"].sum()
    not_bld = n - bld
    u4      = int((sub["units"] == 4).sum())
    u2      = int((sub["units"] == 2).sum())
    units   = u4 * 4 + u2 * 2
    total_units += units
    print(f"{zone:<8} {n:>6} {bld:>10} {not_bld:>10} {u4:>7} {u2:>7} {units:>11,}")

print("-" * 65)
mapped = vacant[vacant["mapped"]]
u4_tot = int((mapped["units"] == 4).sum())
u2_tot = int((mapped["units"] == 2).sum())
print(f"{'MAPPED':<8} {len(mapped):>6} {mapped['buildable'].sum():>10} {(~mapped['buildable']).sum():>10} {u4_tot:>7} {u2_tot:>7} {total_units:>11,}")

unmapped = vacant[~vacant["mapped"]]
print(f"\nUnmapped zones ({len(unmapped)} parcels): {unmapped['zone'].value_counts().to_dict()}")

# ---------------------------------------------------------------------------
# Chart — stacked horizontal bar by zone
# ---------------------------------------------------------------------------
COLOR_4    = "#E07B4C"   # orange  — 4-unit (duplex + duplex ADU)
COLOR_2    = "#F5C48A"   # light orange — 2-unit (duplex only)
COLOR_NONE = "#cccccc"   # gray — not buildable

fig, ax = plt.subplots(figsize=(9, 6))
fig.suptitle("Vacant Residential Lots: Housing Capacity by Zone",
             fontsize=16, fontweight="bold")
ax.set_title(
    "Rules-based estimate under Madison Housing Forward  |  Mapped zones only",
    fontsize=11, color="#555555", pad=8,
)

for i, zone in enumerate(zone_order):
    sub     = vacant[vacant["zone"] == zone]
    n4      = int((sub["units"] == 4).sum())
    n2      = int((sub["units"] == 2).sum())
    n0      = int((sub["units"] == 0).sum())
    pot     = n4 * 4 + n2 * 2

    ax.barh(i, n4,         color=COLOR_4,    height=0.6, left=0,      zorder=3)
    ax.barh(i, n2,         color=COLOR_2,    height=0.6, left=n4,     zorder=3)
    ax.barh(i, n0,         color=COLOR_NONE, height=0.6, left=n4+n2,  zorder=3)

    total_shown = n4 + n2 + n0
    if pot > 0:
        ax.text(total_shown + 2, i, f"{pot:,} units", va="center", fontsize=10, color="#333333")

ax.set_yticks(range(len(zone_order)))
ax.set_yticklabels(zone_order, fontsize=12)
ax.set_xlabel("Number of Parcels", fontsize=12)
ax.grid(axis="x", color="#dddddd", zorder=1)
ax.set_axisbelow(True)
ax.spines[["top", "right"]].set_visible(False)

from matplotlib.patches import Patch
legend_handles = [
    Patch(color=COLOR_4,    label="4 units — duplex + duplex ADU (lot ≥ 6,000 sq ft)"),
    Patch(color=COLOR_2,    label="2 units — duplex only (lot < 6,000 sq ft)"),
    Patch(color=COLOR_NONE, label="Not buildable (lot below zone minimum)"),
]
ax.legend(handles=legend_handles, loc="upper right", fontsize=9, framealpha=0.9)

ax.annotate(
    f"Total potential units (mapped zones): {total_units:,}  |  "
    f"{len(unmapped):,} parcels in unmapped zones (PD, A, CN, etc.) excluded",
    xy=(0.5, -0.12), xycoords="axes fraction", ha="center", fontsize=9, color="#777777",
)

fig.tight_layout()
fig.savefig(os.path.join(CHARTS_DIR, "vacant_zoning_capacity.png"), dpi=150, bbox_inches="tight")
print("\nSaved vacant_zoning_capacity.png")
plt.show()
print("Done.")
