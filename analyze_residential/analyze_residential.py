import os

import geopandas as gpd
import pandas as pd
import numpy as np
import seaborn as sns
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
CHARTS_DIR = os.path.join(SCRIPT_DIR, "charts")
os.makedirs(CHARTS_DIR, exist_ok=True)

# ---------------------------------------------------------------------------
# Load & prepare — Residential only
# ---------------------------------------------------------------------------
print("Loading GeoJSON...")
gdf = gpd.read_file(os.path.join(SCRIPT_DIR, "..", "Tax_Parcels.geojson"), engine="pyogrio")

cols = [
    "PropertyClass", "PropertyUse",
    "CurrentLand", "PreviousLand", "PreviousLand2",
    "CurrentImpr", "PreviousImpr", "PreviousImpr2",
    "CurrentTotal", "PreviousTotal", "PreviousTotal2",
]
df = gdf[cols].copy()
total_current_all = gdf["CurrentTotal"].sum()
total_prev_all    = gdf["PreviousTotal"].sum()
df = df[df["PropertyClass"] == "Residential"].copy()

def pct_chg(curr, prev):
    return np.where(prev != 0, (curr - prev) / prev * 100.0, np.nan)

df["land_pct"]  = pct_chg(df["CurrentLand"],  df["PreviousLand"])
df["impr_pct"]  = pct_chg(df["CurrentImpr"],  df["PreviousImpr"])
df["total_pct"] = pct_chg(df["CurrentTotal"], df["PreviousTotal"])

df["prev_land_pct"]  = pct_chg(df["PreviousLand"],  df["PreviousLand2"])
df["prev_impr_pct"]  = pct_chg(df["PreviousImpr"],  df["PreviousImpr2"])
df["prev_total_pct"] = pct_chg(df["PreviousTotal"], df["PreviousTotal2"])
df["lot_type"]  = df["PropertyUse"].str.lower().str.contains("vacant", na=False) \
                    .map({True: "Vacant", False: "Improved"})

df["current_share"] = df["CurrentTotal"] / total_current_all
df["prev_share"]    = df["PreviousTotal"] / total_prev_all
df["share_pct"]     = np.where(
    df["prev_share"] > 0,
    (df["current_share"] - df["prev_share"]) / df["prev_share"] * 100,
    np.nan,
)

print(f"Residential parcels: {len(df):,}")
print(f"  Improved: {(df['lot_type']=='Improved').sum():,}")
print(f"  Vacant:   {(df['lot_type']=='Vacant').sum():,}")

# ---------------------------------------------------------------------------
# Shared style
# ---------------------------------------------------------------------------
sns.set_theme(style="whitegrid", palette="muted")
FLIER        = dict(marker="o", markersize=2, alpha=0.2, linestyle="none")
MEDIAN_PROPS = dict(color="black", linewidth=2)

def clip(series, lo_q=0.02, hi_q=0.98):
    lo, hi = series.quantile(lo_q), series.quantile(hi_q)
    return series.clip(lo, hi)

# ---------------------------------------------------------------------------
# Figure 1: Land / Improvement / Total % change (residential)
# ---------------------------------------------------------------------------
metric_order = ["Land", "Improvement", "Total"]
metric_map   = {"land_pct": "Land", "impr_pct": "Improvement", "total_pct": "Total"}

long = df[["land_pct", "impr_pct", "total_pct"]].copy()
for col in long.columns:
    long[col] = clip(long[col])
long = long.melt(var_name="metric", value_name="pct").dropna()
long["metric"] = long["metric"].map(metric_map)
long["metric"] = pd.Categorical(long["metric"], categories=metric_order, ordered=True)

fig1, ax1 = plt.subplots(figsize=(7, 6))
fig1.suptitle(
    "Residential Assessment % Change\n(Current vs. Previous)",
    fontsize=14,
)

palette1 = {"Land": "#6AAB6A", "Improvement": "#5B8DB8", "Total": "#9B6BAE"}

sns.boxplot(
    data=long,
    x="metric",
    y="pct",
    hue="metric",
    order=metric_order,
    palette=palette1,
    flierprops=FLIER,
    medianprops=MEDIAN_PROPS,
    width=0.5,
    legend=False,
    ax=ax1,
)
ax1.axhline(0, color="red", linewidth=1, linestyle="--", alpha=0.6)
ax1.set_xlabel("")
ax1.set_ylabel("% Change", fontsize=11)
ax1.yaxis.set_major_formatter(mticker.FuncFormatter(lambda v, _: f"{v:+.0f}%"))

counts1 = long.groupby("metric", observed=True)["pct"].count()
ax1.set_xticks(range(len(metric_order)))
ax1.set_xticklabels([
    f"{m}\n(n={counts1.get(m, 0):,})" for m in metric_order
], fontsize=10)

fig1.text(
    0.5, -0.01,
    "Whiskers = 1.5×IQR  |  Clipped to 2nd–98th percentile",
    ha="center", fontsize=9, color="gray",
)
fig1.tight_layout()
fig1.savefig(os.path.join(CHARTS_DIR, "residential_assessment_changes.png"), dpi=150, bbox_inches="tight")
print("Saved residential_assessment_changes.png")

# ---------------------------------------------------------------------------
# Figure 2: Vacant vs Improved — total % change (residential)
# ---------------------------------------------------------------------------
lot_order = ["All Residential", "Improved", "Vacant"]
palette2  = {"All Residential": "#9B6BAE", "Improved": "#4C8BE0", "Vacant": "#E07B4C"}

plot2 = df[["lot_type", "total_pct"]].copy()
plot2["total_pct"] = clip(plot2["total_pct"])
plot2 = plot2.dropna(subset=["total_pct"])

all_row2 = plot2.copy()
all_row2["lot_type"] = "All Residential"
plot2_combined = pd.concat([all_row2, plot2], ignore_index=True)

fig2, ax2 = plt.subplots(figsize=(7, 7))
fig2.suptitle(
    "Residential Total Value % Change\nVacant vs. Improved Lots (Current vs. Previous)",
    fontsize=14,
)

sns.boxplot(
    data=plot2_combined,
    x="lot_type",
    y="total_pct",
    hue="lot_type",
    order=lot_order,
    palette=palette2,
    flierprops=FLIER,
    medianprops=MEDIAN_PROPS,
    width=0.45,
    legend=False,
    ax=ax2,
)
ax2.axhline(0, color="red", linewidth=1, linestyle="--", alpha=0.6)
ax2.set_xlabel("")
ax2.set_ylabel("Total Value % Change", fontsize=11)
ax2.yaxis.set_major_formatter(mticker.FuncFormatter(lambda v, _: f"{v:+.0f}%"))

counts2 = plot2_combined.groupby("lot_type")["total_pct"].count()
ax2.set_xticks(range(len(lot_order)))
ax2.set_xticklabels([
    f"{lt}\n(n={counts2.get(lt, 0):,})" for lt in lot_order
], fontsize=11)

fig2.text(
    0.5, -0.01,
    "Whiskers = 1.5×IQR  |  Clipped to 2nd–98th percentile",
    ha="center", fontsize=9, color="gray",
)
fig2.tight_layout()
fig2.savefig(os.path.join(CHARTS_DIR, "residential_vacant_vs_improved.png"), dpi=150, bbox_inches="tight")
print("Saved residential_vacant_vs_improved.png")

# ---------------------------------------------------------------------------
# Figure 3: Land / Improvement / Total % change — Prior cycle (Previous2 → Previous)
# ---------------------------------------------------------------------------
prior_metric_map = {
    "prev_land_pct": "Land", "prev_impr_pct": "Improvement", "prev_total_pct": "Total"
}

long_prior = df[["prev_land_pct", "prev_impr_pct", "prev_total_pct"]].copy()
for col in long_prior.columns:
    long_prior[col] = clip(long_prior[col])
long_prior = long_prior.melt(var_name="metric", value_name="pct").dropna()
long_prior["metric"] = long_prior["metric"].map(prior_metric_map)
long_prior["metric"] = pd.Categorical(long_prior["metric"], categories=metric_order, ordered=True)

fig3, ax3 = plt.subplots(figsize=(10, 7))
fig3.suptitle(
    "Residential Assessment % Change\n(Previous vs. Previous2 — Prior Cycle)",
    fontsize=14,
)

sns.boxplot(
    data=long_prior,
    x="metric",
    y="pct",
    hue="metric",
    order=metric_order,
    palette=palette1,
    flierprops=FLIER,
    medianprops=MEDIAN_PROPS,
    width=0.5,
    legend=False,
    ax=ax3,
)
ax3.axhline(0, color="red", linewidth=1, linestyle="--", alpha=0.6)
ax3.set_xlabel("")
ax3.set_ylabel("% Change", fontsize=11)
ax3.yaxis.set_major_formatter(mticker.FuncFormatter(lambda v, _: f"{v:+.0f}%"))

counts3 = long_prior.groupby("metric", observed=True)["pct"].count()
ax3.set_xticks(range(len(metric_order)))
ax3.set_xticklabels([
    f"{m}\n(n={counts3.get(m, 0):,})" for m in metric_order
], fontsize=10)

fig3.text(
    0.5, -0.01,
    "Whiskers = 1.5×IQR  |  Clipped to 2nd–98th percentile",
    ha="center", fontsize=9, color="gray",
)
fig3.tight_layout()
fig3.savefig(os.path.join(CHARTS_DIR, "residential_assessment_changes_prior.png"), dpi=150, bbox_inches="tight")
print("Saved residential_assessment_changes_prior.png")

# ---------------------------------------------------------------------------
# Figure 4: Vacant vs Improved — Prior cycle total % change
# ---------------------------------------------------------------------------
plot4 = df[["lot_type", "prev_total_pct"]].copy()
plot4["prev_total_pct"] = clip(plot4["prev_total_pct"])
plot4 = plot4.dropna(subset=["prev_total_pct"])

fig4, ax4 = plt.subplots(figsize=(8, 7))
fig4.suptitle(
    "Residential Total Value % Change\nVacant vs. Improved Lots (Previous vs. Previous2 — Prior Cycle)",
    fontsize=14,
)

sns.boxplot(
    data=plot4,
    x="lot_type",
    y="prev_total_pct",
    hue="lot_type",
    order=lot_order,
    palette=palette2,
    flierprops=FLIER,
    medianprops=MEDIAN_PROPS,
    width=0.45,
    legend=False,
    ax=ax4,
)
ax4.axhline(0, color="red", linewidth=1, linestyle="--", alpha=0.6)
ax4.set_xlabel("")
ax4.set_ylabel("Total Value % Change", fontsize=11)
ax4.yaxis.set_major_formatter(mticker.FuncFormatter(lambda v, _: f"{v:+.0f}%"))

counts4 = plot4.groupby("lot_type")["prev_total_pct"].count()
ax4.set_xticks(range(len(lot_order)))
ax4.set_xticklabels([
    f"{lt}\n(n={counts4.get(lt, 0):,})" for lt in lot_order
], fontsize=11)

fig4.text(
    0.5, -0.01,
    "Whiskers = 1.5×IQR  |  Clipped to 2nd–98th percentile",
    ha="center", fontsize=9, color="gray",
)
fig4.tight_layout()
fig4.savefig(os.path.join(CHARTS_DIR, "residential_vacant_vs_improved_prior.png"), dpi=150, bbox_inches="tight")
print("Saved residential_vacant_vs_improved_prior.png")

# ---------------------------------------------------------------------------
# Figure 5: Tax share delta — All Residential, Improved, Vacant (combined)
# ---------------------------------------------------------------------------
share_base = df[["lot_type", "share_pct"]].copy()
share_base["share_pct"] = clip(share_base["share_pct"])
share_base = share_base.dropna(subset=["share_pct"])

all_row = share_base.copy()
all_row["lot_type"] = "All Residential"
share_combined = pd.concat([all_row, share_base], ignore_index=True)

group_order   = ["All Residential", "Improved", "Vacant"]
palette_share = {"All Residential": "#9B6BAE", "Improved": "#4C8BE0", "Vacant": "#E07B4C"}

fig5, ax5 = plt.subplots(figsize=(10, 7))
fig5.suptitle(
    "Residential Tax Share Change\n(Current vs. Previous)",
    fontsize=14,
)

sns.boxplot(
    data=share_combined,
    x="lot_type",
    y="share_pct",
    hue="lot_type",
    order=group_order,
    palette=palette_share,
    flierprops=FLIER,
    medianprops=MEDIAN_PROPS,
    width=0.5,
    legend=False,
    ax=ax5,
)
ax5.axhline(0, color="red", linewidth=1, linestyle="--", alpha=0.6)
ax5.set_xlabel("")
ax5.set_ylabel("Share Change (%)", fontsize=11)
ax5.yaxis.set_major_formatter(mticker.FuncFormatter(lambda v, _: f"{v:+.0f}%"))

counts5 = share_combined.groupby("lot_type", observed=True)["share_pct"].count()
ax5.set_xticks(range(len(group_order)))
ax5.set_xticklabels([
    f"{g}\n(n={counts5.get(g, 0):,})" for g in group_order
], fontsize=10)

fig5.text(
    0.5, -0.01,
    "Positive = parcel now bears a larger share of the levy  |  Clipped to 2nd–98th percentile",
    ha="center", fontsize=9, color="gray",
)
fig5.tight_layout()
fig5.savefig(os.path.join(CHARTS_DIR, "residential_share_delta.png"), dpi=150, bbox_inches="tight")
print("Saved residential_share_delta.png")

plt.show()
print("Done.")
