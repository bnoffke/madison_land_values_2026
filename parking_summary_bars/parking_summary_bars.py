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

for col in ["land_pct", "impr_pct", "total_pct", "prev_land_pct", "prev_impr_pct", "prev_total_pct"]:
    lo, hi = df[col].quantile(0.02), df[col].quantile(0.98)
    df[col] = df[col].clip(lo, hi)

labels  = ["Land Value", "Improvement\nValue", "Total Value"]
colors  = ["#5B8DB8", "#6AAB6A", "#9B6BAE"]
type_labels  = ["Lots", "Ramps"]
type_colors  = ["#4C8BE0", "#E07B4C"]

def bar_chart(ax, fig, bar_labels, vals, bar_colors, suptitle, subtitle):
    fig.suptitle(suptitle, fontsize=16, fontweight="bold", y=0.98)
    ax.set_title(subtitle, fontsize=11, color="#555555", pad=8)
    bars = ax.bar(bar_labels, vals, color=bar_colors, width=0.5, zorder=3)
    y_span = max(vals) - min(0, min(vals))
    ax.set_ylim(bottom=min(0, min(vals)) - y_span * 0.4)
    ax.axhline(0, color="#333333", linewidth=1, zorder=2)
    ax.set_ylabel("Average % Change", fontsize=12)
    ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda v, _: f"{v:+.0f}%"))
    ax.grid(axis="y", color="#dddddd", zorder=1)
    ax.set_axisbelow(True)
    ax.tick_params(axis="x", labelsize=12)
    ax.spines[["top", "right", "left"]].set_visible(False)
    ax.tick_params(left=False)
    for bar, val in zip(bars, vals):
        pad = 0.3 if val >= 0 else -0.3
        va  = "bottom" if val >= 0 else "top"
        ax.text(bar.get_x() + bar.get_width() / 2, val + pad,
                f"{val:+.1f}%", ha="center", va=va,
                fontsize=13, fontweight="bold", color="#222222")
    return bars

# ---------------------------------------------------------------------------
# Figure 1: Mean % change — Land, Improvement, Total
# ---------------------------------------------------------------------------
means = [df["land_pct"].mean(), df["impr_pct"].mean(), df["total_pct"].mean()]

fig1, ax1 = plt.subplots(figsize=(8, 6))
bar_chart(ax1, fig1, labels, means, colors,
          "Average Parking Assessment Change",
          "Current vs. Previous Assessment")
ax1.annotate(
    "Improvement value = structures/buildings on the land  |  Extreme outliers trimmed (2nd–98th pct)",
    xy=(0.5, -0.12), xycoords="axes fraction", ha="center", fontsize=9, color="#777777",
)
fig1.tight_layout()
fig1.savefig(os.path.join(CHARTS_DIR, "parking_mean_changes.png"), dpi=150, bbox_inches="tight")
print("Saved parking_mean_changes.png")

# ---------------------------------------------------------------------------
# Figure 2: Mean total % change — Lot vs Ramp
# ---------------------------------------------------------------------------
type_means = df.groupby("parking_type")["total_pct"].mean()
type_vals  = [type_means["Lot"], type_means["Ramp"]]

fig2, ax2 = plt.subplots(figsize=(7, 6))
ax2.set_ylabel("Average % Change in Total Value", fontsize=12)
bar_chart(ax2, fig2, type_labels, type_vals, type_colors,
          "Lots vs. Ramps:\nAverage Total Value Change",
          "Current vs. Previous Assessment")
fig2.tight_layout()
fig2.savefig(os.path.join(CHARTS_DIR, "parking_lot_vs_ramp_means.png"), dpi=150, bbox_inches="tight")
print("Saved parking_lot_vs_ramp_means.png")

# ---------------------------------------------------------------------------
# Figure 3: Mean % change — prior cycle
# ---------------------------------------------------------------------------
prior_means = [df["prev_land_pct"].mean(), df["prev_impr_pct"].mean(), df["prev_total_pct"].mean()]

fig3, ax3 = plt.subplots(figsize=(8, 6))
bar_chart(ax3, fig3, labels, prior_means, colors,
          "Average Parking Assessment Change",
          "Previous vs. Previous2 Assessment (Prior Cycle)")
ax3.annotate(
    "Improvement value = structures/buildings on the land  |  Extreme outliers trimmed (2nd–98th pct)",
    xy=(0.5, -0.12), xycoords="axes fraction", ha="center", fontsize=9, color="#777777",
)
fig3.tight_layout()
fig3.savefig(os.path.join(CHARTS_DIR, "parking_mean_changes_prior.png"), dpi=150, bbox_inches="tight")
print("Saved parking_mean_changes_prior.png")

# ---------------------------------------------------------------------------
# Figure 4: Mean total % change — prior cycle, Lot vs Ramp
# ---------------------------------------------------------------------------
prior_type_means = df.groupby("parking_type")["prev_total_pct"].mean()
prior_type_vals  = [prior_type_means["Lot"], prior_type_means["Ramp"]]

fig4, ax4 = plt.subplots(figsize=(7, 6))
ax4.set_ylabel("Average % Change in Total Value", fontsize=12)
bar_chart(ax4, fig4, type_labels, prior_type_vals, type_colors,
          "Lots vs. Ramps:\nAverage Total Value Change",
          "Previous vs. Previous2 Assessment (Prior Cycle)")
fig4.tight_layout()
fig4.savefig(os.path.join(CHARTS_DIR, "parking_lot_vs_ramp_means_prior.png"), dpi=150, bbox_inches="tight")
print("Saved parking_lot_vs_ramp_means_prior.png")

plt.show()
print("Done.")
