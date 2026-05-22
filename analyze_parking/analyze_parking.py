import geopandas as gpd
import pandas as pd
import numpy as np
import seaborn as sns
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker

print("Loading GeoJSON...")
gdf = gpd.read_file("Tax_Parcels.geojson", engine="pyogrio")

cols = [
    "PropertyClass", "PropertyUse",
    "CurrentLand", "PreviousLand", "PreviousLand2",
    "CurrentImpr", "PreviousImpr", "PreviousImpr2",
    "CurrentTotal", "PreviousTotal", "PreviousTotal2",
]
df = gdf[cols].copy()
df = df[df["PropertyUse"].str.lower().str.contains("parking", na=False)].copy()

def pct_chg(curr, prev):
    return np.where(prev != 0, (curr - prev) / prev * 100.0, np.nan)

df["land_pct"]  = pct_chg(df["CurrentLand"],  df["PreviousLand"])
df["impr_pct"]  = pct_chg(df["CurrentImpr"],  df["PreviousImpr"])
df["total_pct"] = pct_chg(df["CurrentTotal"], df["PreviousTotal"])

df["prev_land_pct"]  = pct_chg(df["PreviousLand"],  df["PreviousLand2"])
df["prev_impr_pct"]  = pct_chg(df["PreviousImpr"],  df["PreviousImpr2"])
df["prev_total_pct"] = pct_chg(df["PreviousTotal"], df["PreviousTotal2"])

df["parking_type"] = df["PropertyUse"].str.lower().str.contains("ramp", na=False) \
                        .map({True: "Ramp", False: "Lot"})

print(f"Parking parcels: {len(df):,}")
print(f"  Ramp: {(df['parking_type']=='Ramp').sum():,}")
print(f"  Lot:  {(df['parking_type']=='Lot').sum():,}")

sns.set_theme(style="whitegrid", palette="muted")
FLIER        = dict(marker="o", markersize=3, alpha=0.3, linestyle="none")
MEDIAN_PROPS = dict(color="black", linewidth=2)

def clip(series, lo_q=0.02, hi_q=0.98):
    lo, hi = series.quantile(lo_q), series.quantile(hi_q)
    return series.clip(lo, hi)

metric_order = ["Land", "Improvement", "Total"]
metric_map   = {"land_pct": "Land", "impr_pct": "Improvement", "total_pct": "Total"}
palette1     = {"Land": "#5B8DB8", "Improvement": "#6AAB6A", "Total": "#9B6BAE"}
type_order   = ["Lot", "Ramp"]
palette2     = {"Lot": "#4C8BE0", "Ramp": "#E07B4C"}

# ---------------------------------------------------------------------------
# Figure 1: Land / Improvement / Total % change — current cycle
# ---------------------------------------------------------------------------
long = df[["land_pct", "impr_pct", "total_pct"]].copy()
for col in long.columns:
    long[col] = clip(long[col])
long = long.melt(var_name="metric", value_name="pct").dropna()
long["metric"] = long["metric"].map(metric_map)
long["metric"] = pd.Categorical(long["metric"], categories=metric_order, ordered=True)

fig1, ax1 = plt.subplots(figsize=(10, 7))
fig1.suptitle(
    "Parking Assessment % Change\n(Current vs. Previous)",
    fontsize=14,
)

sns.boxplot(
    data=long, x="metric", y="pct", hue="metric",
    order=metric_order, palette=palette1,
    flierprops=FLIER, medianprops=MEDIAN_PROPS,
    width=0.5, legend=False, ax=ax1,
)
ax1.axhline(0, color="red", linewidth=1, linestyle="--", alpha=0.6)
ax1.set_xlabel("")
ax1.set_ylabel("% Change", fontsize=11)
ax1.yaxis.set_major_formatter(mticker.FuncFormatter(lambda v, _: f"{v:+.0f}%"))

counts1 = long.groupby("metric", observed=True)["pct"].count()
ax1.set_xticks(range(len(metric_order)))
ax1.set_xticklabels([f"{m}\n(n={counts1.get(m, 0):,})" for m in metric_order], fontsize=10)

fig1.text(0.5, -0.01, "Whiskers = 1.5×IQR  |  Clipped to 2nd–98th percentile",
          ha="center", fontsize=9, color="gray")
fig1.tight_layout()
fig1.savefig("parking_assessment_changes.png", dpi=150, bbox_inches="tight")
print("Saved parking_assessment_changes.png")

# ---------------------------------------------------------------------------
# Figure 2: Lot vs Ramp — total % change
# ---------------------------------------------------------------------------
plot2 = df[["parking_type", "total_pct"]].copy()
plot2["total_pct"] = clip(plot2["total_pct"])
plot2 = plot2.dropna(subset=["total_pct"])

fig2, ax2 = plt.subplots(figsize=(8, 7))
fig2.suptitle(
    "Parking Total Value % Change\nLot vs. Ramp (Current vs. Previous)",
    fontsize=14,
)

sns.boxplot(
    data=plot2, x="parking_type", y="total_pct", hue="parking_type",
    order=type_order, palette=palette2,
    flierprops=FLIER, medianprops=MEDIAN_PROPS,
    width=0.45, legend=False, ax=ax2,
)
ax2.axhline(0, color="red", linewidth=1, linestyle="--", alpha=0.6)
ax2.set_xlabel("")
ax2.set_ylabel("Total Value % Change", fontsize=11)
ax2.yaxis.set_major_formatter(mticker.FuncFormatter(lambda v, _: f"{v:+.0f}%"))

counts2 = plot2.groupby("parking_type")["total_pct"].count()
ax2.set_xticks(range(len(type_order)))
ax2.set_xticklabels([f"{t}\n(n={counts2.get(t, 0):,})" for t in type_order], fontsize=11)

fig2.text(0.5, -0.01, "Whiskers = 1.5×IQR  |  Clipped to 2nd–98th percentile",
          ha="center", fontsize=9, color="gray")
fig2.tight_layout()
fig2.savefig("parking_lot_vs_ramp.png", dpi=150, bbox_inches="tight")
print("Saved parking_lot_vs_ramp.png")

# ---------------------------------------------------------------------------
# Figure 3: Land / Improvement / Total % change — prior cycle
# ---------------------------------------------------------------------------
prior_metric_map = {"prev_land_pct": "Land", "prev_impr_pct": "Improvement", "prev_total_pct": "Total"}

long_prior = df[["prev_land_pct", "prev_impr_pct", "prev_total_pct"]].copy()
for col in long_prior.columns:
    long_prior[col] = clip(long_prior[col])
long_prior = long_prior.melt(var_name="metric", value_name="pct").dropna()
long_prior["metric"] = long_prior["metric"].map(prior_metric_map)
long_prior["metric"] = pd.Categorical(long_prior["metric"], categories=metric_order, ordered=True)

fig3, ax3 = plt.subplots(figsize=(10, 7))
fig3.suptitle(
    "Parking Assessment % Change\n(Previous vs. Previous2 — Prior Cycle)",
    fontsize=14,
)

sns.boxplot(
    data=long_prior, x="metric", y="pct", hue="metric",
    order=metric_order, palette=palette1,
    flierprops=FLIER, medianprops=MEDIAN_PROPS,
    width=0.5, legend=False, ax=ax3,
)
ax3.axhline(0, color="red", linewidth=1, linestyle="--", alpha=0.6)
ax3.set_xlabel("")
ax3.set_ylabel("% Change", fontsize=11)
ax3.yaxis.set_major_formatter(mticker.FuncFormatter(lambda v, _: f"{v:+.0f}%"))

counts3 = long_prior.groupby("metric", observed=True)["pct"].count()
ax3.set_xticks(range(len(metric_order)))
ax3.set_xticklabels([f"{m}\n(n={counts3.get(m, 0):,})" for m in metric_order], fontsize=10)

fig3.text(0.5, -0.01, "Whiskers = 1.5×IQR  |  Clipped to 2nd–98th percentile",
          ha="center", fontsize=9, color="gray")
fig3.tight_layout()
fig3.savefig("parking_assessment_changes_prior.png", dpi=150, bbox_inches="tight")
print("Saved parking_assessment_changes_prior.png")

# ---------------------------------------------------------------------------
# Figure 4: Lot vs Ramp — prior cycle total % change
# ---------------------------------------------------------------------------
plot4 = df[["parking_type", "prev_total_pct"]].copy()
plot4["prev_total_pct"] = clip(plot4["prev_total_pct"])
plot4 = plot4.dropna(subset=["prev_total_pct"])

fig4, ax4 = plt.subplots(figsize=(8, 7))
fig4.suptitle(
    "Parking Total Value % Change\nLot vs. Ramp (Previous vs. Previous2 — Prior Cycle)",
    fontsize=14,
)

sns.boxplot(
    data=plot4, x="parking_type", y="prev_total_pct", hue="parking_type",
    order=type_order, palette=palette2,
    flierprops=FLIER, medianprops=MEDIAN_PROPS,
    width=0.45, legend=False, ax=ax4,
)
ax4.axhline(0, color="red", linewidth=1, linestyle="--", alpha=0.6)
ax4.set_xlabel("")
ax4.set_ylabel("Total Value % Change", fontsize=11)
ax4.yaxis.set_major_formatter(mticker.FuncFormatter(lambda v, _: f"{v:+.0f}%"))

counts4 = plot4.groupby("parking_type")["prev_total_pct"].count()
ax4.set_xticks(range(len(type_order)))
ax4.set_xticklabels([f"{t}\n(n={counts4.get(t, 0):,})" for t in type_order], fontsize=11)

fig4.text(0.5, -0.01, "Whiskers = 1.5×IQR  |  Clipped to 2nd–98th percentile",
          ha="center", fontsize=9, color="gray")
fig4.tight_layout()
fig4.savefig("parking_lot_vs_ramp_prior.png", dpi=150, bbox_inches="tight")
print("Saved parking_lot_vs_ramp_prior.png")

plt.show()
print("Done.")
