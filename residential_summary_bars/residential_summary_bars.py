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
total_current_all = gdf["CurrentTotal"].sum()
total_prev_all    = gdf["PreviousTotal"].sum()
df = df[df["PropertyClass"] == "Residential"].copy()

df["lot_type"] = df["PropertyUse"].str.lower().str.contains("vacant", na=False) \
                    .map({True: "Vacant", False: "Improved"})

def pct_chg(curr, prev):
    return np.where(prev != 0, (curr - prev) / prev * 100.0, np.nan)

df["land_pct"]  = pct_chg(df["CurrentLand"],  df["PreviousLand"])
df["impr_pct"]  = pct_chg(df["CurrentImpr"],  df["PreviousImpr"])
df["total_pct"] = pct_chg(df["CurrentTotal"], df["PreviousTotal"])

df["prev_land_pct"]  = pct_chg(df["PreviousLand"],  df["PreviousLand2"])
df["prev_impr_pct"]  = pct_chg(df["PreviousImpr"],  df["PreviousImpr2"])
df["prev_total_pct"] = pct_chg(df["PreviousTotal"], df["PreviousTotal2"])

df["current_share"] = df["CurrentTotal"] / total_current_all
df["prev_share"]    = df["PreviousTotal"] / total_prev_all
df["share_pct"]     = np.where(
    df["prev_share"] > 0,
    (df["current_share"] - df["prev_share"]) / df["prev_share"] * 100,
    np.nan,
)

land_alloc = {
    "2024": df["PreviousLand2"].sum() / df["PreviousTotal2"].sum() * 100,
    "2025": df["PreviousLand"].sum()  / df["PreviousTotal"].sum()  * 100,
    "2026": df["CurrentLand"].sum()   / df["CurrentTotal"].sum()   * 100,
}

for col in ["land_pct", "impr_pct", "total_pct", "prev_land_pct", "prev_impr_pct", "prev_total_pct", "share_pct"]:
    lo, hi = df[col].quantile(0.02), df[col].quantile(0.98)
    df[col] = df[col].clip(lo, hi)

TRIM_NOTE = "Trimmed mean — top and bottom 2% of parcels excluded to remove data anomalies"

# ---------------------------------------------------------------------------
# Figure 1: Mean % change — Land, Improvement, Total
# ---------------------------------------------------------------------------
labels  = ["Land Value", "Improvement\nValue", "Total Value"]
means   = [df["land_pct"].mean(), df["impr_pct"].mean(), df["total_pct"].mean()]
colors  = ["#6AAB6A", "#5B8DB8", "#9B6BAE"]

fig1, ax1 = plt.subplots(figsize=(8, 6))
fig1.suptitle(
    "Average Residential Assessment Change",
    fontsize=16, fontweight="bold", y=0.98,
)
ax1.set_title("Current vs. Previous Assessment", fontsize=11, color="#555555", pad=8)

bars = ax1.bar(labels, means, color=colors, width=0.5, zorder=3)
ax1.axhline(0, color="#333333", linewidth=1, zorder=2)
ax1.set_ylabel("Average % Change", fontsize=12)
ax1.yaxis.set_major_formatter(mticker.FuncFormatter(lambda v, _: f"{v:+.0f}%"))
ax1.grid(axis="y", color="#dddddd", zorder=1)
ax1.set_axisbelow(True)
ax1.tick_params(axis="x", labelsize=12)
ax1.spines[["top", "right", "left"]].set_visible(False)
ax1.tick_params(left=False)

for bar, val in zip(bars, means):
    pad   = 0.3 if val >= 0 else -0.3
    va    = "bottom" if val >= 0 else "top"
    ax1.text(
        bar.get_x() + bar.get_width() / 2,
        val + pad,
        f"{val:+.1f}%",
        ha="center", va=va,
        fontsize=13, fontweight="bold", color="#222222",
    )

ax1.annotate(TRIM_NOTE, xy=(0.5, -0.12), xycoords="axes fraction",
             ha="center", fontsize=9, color="#777777")

fig1.tight_layout()
fig1.savefig(os.path.join(CHARTS_DIR, "residential_mean_changes.png"), dpi=150, bbox_inches="tight")
print("Saved residential_mean_changes.png")

# ---------------------------------------------------------------------------
# Figure 2: Mean total % change — Improved vs Vacant
# ---------------------------------------------------------------------------
lot_means  = df.groupby("lot_type")["total_pct"].mean()
lot_labels = ["Improved Lots", "Vacant Lots"]
lot_vals   = [lot_means["Improved"], lot_means["Vacant"]]
lot_colors = ["#4C8BE0", "#E07B4C"]

fig2, ax2 = plt.subplots(figsize=(7, 6))
fig2.suptitle(
    "Vacant vs. Improved Lots:\nAverage Total Value Change",
    fontsize=16, fontweight="bold", y=1.0,
)
ax2.set_title("Residential properties only", fontsize=11, color="#555555", pad=8)

bars2 = ax2.bar(lot_labels, lot_vals, color=lot_colors, width=0.45, zorder=3)
ax2.axhline(0, color="#333333", linewidth=1, zorder=2)
ax2.set_ylabel("Average % Change in Total Value", fontsize=12)
ax2.yaxis.set_major_formatter(mticker.FuncFormatter(lambda v, _: f"{v:+.0f}%"))
ax2.grid(axis="y", color="#dddddd", zorder=1)
ax2.set_axisbelow(True)
ax2.tick_params(axis="x", labelsize=13)
ax2.spines[["top", "right", "left"]].set_visible(False)
ax2.tick_params(left=False)

for bar, val in zip(bars2, lot_vals):
    pad = 0.3 if val >= 0 else -0.3
    va  = "bottom" if val >= 0 else "top"
    ax2.text(
        bar.get_x() + bar.get_width() / 2,
        val + pad,
        f"{val:+.1f}%",
        ha="center", va=va,
        fontsize=15, fontweight="bold", color="#222222",
    )

ax2.annotate(TRIM_NOTE, xy=(0.5, -0.12), xycoords="axes fraction",
             ha="center", fontsize=9, color="#777777")

fig2.tight_layout()
fig2.savefig(os.path.join(CHARTS_DIR, "residential_vacant_vs_improved_means.png"), dpi=150, bbox_inches="tight")
print("Saved residential_vacant_vs_improved_means.png")

# ---------------------------------------------------------------------------
# Figure 3: Mean % change — Prior cycle (Previous2 → Previous)
# ---------------------------------------------------------------------------
prior_means = [df["prev_land_pct"].mean(), df["prev_impr_pct"].mean(), df["prev_total_pct"].mean()]

fig3, ax3 = plt.subplots(figsize=(8, 6))
fig3.suptitle(
    "Average Residential Assessment Change",
    fontsize=16, fontweight="bold", y=0.98,
)
ax3.set_title("Previous vs. Previous2 Assessment (Prior Cycle)", fontsize=11, color="#555555", pad=8)

bars3 = ax3.bar(labels, prior_means, color=colors, width=0.5, zorder=3)
ax3.axhline(0, color="#333333", linewidth=1, zorder=2)
ax3.set_ylabel("Average % Change", fontsize=12)
ax3.yaxis.set_major_formatter(mticker.FuncFormatter(lambda v, _: f"{v:+.0f}%"))
ax3.grid(axis="y", color="#dddddd", zorder=1)
ax3.set_axisbelow(True)
ax3.tick_params(axis="x", labelsize=12)
ax3.spines[["top", "right", "left"]].set_visible(False)
ax3.tick_params(left=False)

for bar, val in zip(bars3, prior_means):
    pad = 0.3 if val >= 0 else -0.3
    va  = "bottom" if val >= 0 else "top"
    ax3.text(
        bar.get_x() + bar.get_width() / 2,
        val + pad,
        f"{val:+.1f}%",
        ha="center", va=va,
        fontsize=13, fontweight="bold", color="#222222",
    )

ax3.annotate(TRIM_NOTE, xy=(0.5, -0.12), xycoords="axes fraction",
             ha="center", fontsize=9, color="#777777")

fig3.tight_layout()
fig3.savefig(os.path.join(CHARTS_DIR, "residential_mean_changes_prior.png"), dpi=150, bbox_inches="tight")
print("Saved residential_mean_changes_prior.png")

# ---------------------------------------------------------------------------
# Figure 4: Mean total % change — Prior cycle, Improved vs Vacant
# ---------------------------------------------------------------------------
prior_lot_means = df.groupby("lot_type")["prev_total_pct"].mean()
prior_lot_vals  = [prior_lot_means["Improved"], prior_lot_means["Vacant"]]

fig4, ax4 = plt.subplots(figsize=(7, 6))
fig4.suptitle(
    "Vacant vs. Improved Lots:\nAverage Total Value Change",
    fontsize=16, fontweight="bold", y=1.0,
)
ax4.set_title("Previous vs. Previous2 Assessment (Prior Cycle)", fontsize=11, color="#555555", pad=8)

bars4 = ax4.bar(lot_labels, prior_lot_vals, color=lot_colors, width=0.45, zorder=3)
ax4.set_ylim(0, max(prior_lot_vals) * 1.35)
ax4.axhline(0, color="#333333", linewidth=1, zorder=2)
ax4.set_ylabel("Average % Change in Total Value", fontsize=12)
ax4.yaxis.set_major_formatter(mticker.FuncFormatter(lambda v, _: f"{v:+.0f}%"))
ax4.grid(axis="y", color="#dddddd", zorder=1)
ax4.set_axisbelow(True)
ax4.tick_params(axis="x", labelsize=13)
ax4.spines[["top", "right", "left"]].set_visible(False)
ax4.tick_params(left=False)

for bar, val in zip(bars4, prior_lot_vals):
    pad = 0.3 if val >= 0 else -0.3
    va  = "bottom" if val >= 0 else "top"
    ax4.text(
        bar.get_x() + bar.get_width() / 2,
        val + pad,
        f"{val:+.1f}%",
        ha="center", va=va,
        fontsize=15, fontweight="bold", color="#222222",
    )

ax4.annotate(TRIM_NOTE, xy=(0.5, -0.12), xycoords="axes fraction",
             ha="center", fontsize=9, color="#777777")

fig4.tight_layout()
fig4.savefig(os.path.join(CHARTS_DIR, "residential_vacant_vs_improved_means_prior.png"), dpi=150, bbox_inches="tight")
print("Saved residential_vacant_vs_improved_means_prior.png")

# ---------------------------------------------------------------------------
# Figure 5: Mean share % change — All Residential, Improved, Vacant
# ---------------------------------------------------------------------------
share_labels = ["All\nResidential", "Improved\nLots", "Vacant\nLots"]
share_vals = [
    df["share_pct"].mean(),
    df[df["lot_type"] == "Improved"]["share_pct"].mean(),
    df[df["lot_type"] == "Vacant"]["share_pct"].mean(),
]
share_colors = ["#9B6BAE", "#4C8BE0", "#E07B4C"]

fig5, ax5 = plt.subplots(figsize=(6, 7))
fig5.suptitle(
    "Average Residential Tax Share Change",
    fontsize=16, fontweight="bold", y=0.98,
)
ax5.set_title("Share of total assessed value — Current vs. Previous", fontsize=11, color="#555555", pad=8)

bars5 = ax5.bar(share_labels, share_vals, color=share_colors, width=0.5, zorder=3)
y_span = max(share_vals) - min(0, min(share_vals))
ax5.set_ylim(
    bottom=min(0, min(share_vals)) - y_span * 0.4,
    top=max(share_vals) * 1.35,
)
ax5.axhline(0, color="#333333", linewidth=1, zorder=2)
ax5.set_ylabel("Average % Change in Tax Share", fontsize=12)
ax5.yaxis.set_major_formatter(mticker.FuncFormatter(lambda v, _: f"{v:+.0f}%"))
ax5.grid(axis="y", color="#dddddd", zorder=1)
ax5.set_axisbelow(True)
ax5.tick_params(axis="x", labelsize=12)
ax5.spines[["top", "right", "left"]].set_visible(False)
ax5.tick_params(left=False)

for bar, val in zip(bars5, share_vals):
    pad = 0.3 if val >= 0 else -0.3
    va  = "bottom" if val >= 0 else "top"
    ax5.text(
        bar.get_x() + bar.get_width() / 2,
        val + pad,
        f"{val:+.1f}%",
        ha="center", va=va,
        fontsize=13, fontweight="bold", color="#222222",
    )

ax5.annotate(TRIM_NOTE, xy=(0.5, -0.12), xycoords="axes fraction",
             ha="center", fontsize=9, color="#777777")

fig5.tight_layout()
fig5.savefig(os.path.join(CHARTS_DIR, "residential_share_delta_means.png"), dpi=150, bbox_inches="tight")
print("Saved residential_share_delta_means.png")

# ---------------------------------------------------------------------------
# Figure 6: Land allocation over time (2024 / 2025 / 2026)
# ---------------------------------------------------------------------------
alloc_years  = ["2024", "2025", "2026"]
alloc_vals   = [land_alloc[y] for y in alloc_years]
alloc_colors = ["#c8e6c8", "#c8e6c8", "#6AAB6A"]

fig6, ax6 = plt.subplots(figsize=(6, 6))
fig6.suptitle(
    "Residential Land Allocation Over Time",
    fontsize=16, fontweight="bold", y=0.98,
)
ax6.set_title("Land value as % of total assessed value", fontsize=11, color="#555555", pad=8)

bars6 = ax6.bar(alloc_years, alloc_vals, color=alloc_colors, width=0.5, zorder=3)
ax6.set_ylabel("% of Total Assessed Value", fontsize=12)
ax6.yaxis.set_major_formatter(mticker.FuncFormatter(lambda v, _: f"{v:.1f}%"))
ax6.grid(axis="y", color="#dddddd", zorder=1)
ax6.set_axisbelow(True)
ax6.spines[["top", "right", "left"]].set_visible(False)
ax6.tick_params(left=False, axis="x", labelsize=13)

for bar, val in zip(bars6, alloc_vals):
    ax6.text(
        bar.get_x() + bar.get_width() / 2,
        val + 0.3,
        f"{val:.1f}%",
        ha="center", va="bottom",
        fontsize=13, fontweight="bold", color="#222222",
    )

ax6.annotate(
    "Aggregate: Σ land / Σ total  |  Residential parcels only",
    xy=(0.5, -0.10), xycoords="axes fraction",
    ha="center", fontsize=9, color="#777777",
)

fig6.tight_layout()
fig6.savefig(os.path.join(CHARTS_DIR, "residential_land_allocation_over_time.png"), dpi=150, bbox_inches="tight")
print("Saved residential_land_allocation_over_time.png")

# ---------------------------------------------------------------------------
# Figure 7: Median % change — Land, Improvement, Total
# ---------------------------------------------------------------------------
med_labels = ["Land Value", "Improvement\nValue", "Total Value"]
med_vals   = [df["land_pct"].median(), df["impr_pct"].median(), df["total_pct"].median()]

fig7, ax7 = plt.subplots(figsize=(8, 6))
fig7.suptitle(
    "Median Residential Assessment Change",
    fontsize=16, fontweight="bold", y=0.98,
)
ax7.set_title("Current vs. Previous Assessment  |  Median per parcel", fontsize=11, color="#555555", pad=8)

bars7 = ax7.bar(med_labels, med_vals, color=colors, width=0.5, zorder=3)
ax7.axhline(0, color="#333333", linewidth=1, zorder=2)
ax7.set_ylabel("Median % Change", fontsize=12)
ax7.yaxis.set_major_formatter(mticker.FuncFormatter(lambda v, _: f"{v:+.0f}%"))
ax7.grid(axis="y", color="#dddddd", zorder=1)
ax7.set_axisbelow(True)
ax7.tick_params(axis="x", labelsize=12)
ax7.spines[["top", "right", "left"]].set_visible(False)
ax7.tick_params(left=False)

for bar, val in zip(bars7, med_vals):
    pad = 0.3 if val >= 0 else -0.3
    va  = "bottom" if val >= 0 else "top"
    ax7.text(
        bar.get_x() + bar.get_width() / 2,
        val + pad,
        f"{val:+.1f}%",
        ha="center", va=va,
        fontsize=13, fontweight="bold", color="#222222",
    )

ax7.annotate(
    "Median of per-parcel % changes — represents the typical homeowner, not the tax base aggregate",
    xy=(0.5, -0.12), xycoords="axes fraction",
    ha="center", fontsize=9, color="#777777",
)

fig7.tight_layout()
fig7.savefig(os.path.join(CHARTS_DIR, "residential_median_changes.png"), dpi=150, bbox_inches="tight")
print("Saved residential_median_changes.png")

# ---------------------------------------------------------------------------
# Figure 8: Aggregate vs. Median — stacked subplots (mobile-friendly)
# ---------------------------------------------------------------------------
bar_labels = ["Land\nValue", "Improvement\nValue", "Total\nValue"]

agg_vals = [
    (df["CurrentLand"].sum()  - df["PreviousLand"].sum())  / df["PreviousLand"].sum()  * 100,
    (df["CurrentImpr"].sum()  - df["PreviousImpr"].sum())  / df["PreviousImpr"].sum()  * 100,
    (df["CurrentTotal"].sum() - df["PreviousTotal"].sum()) / df["PreviousTotal"].sum() * 100,
]
med_vals = [df["land_pct"].median(), df["impr_pct"].median(), df["total_pct"].median()]

fig8, (ax_top, ax_bot) = plt.subplots(2, 1, figsize=(6, 10), sharey=True)
fig8.suptitle("Residential Assessment Change\nCurrent vs. Previous", fontsize=16, fontweight="bold")

for ax, vals, subtitle, note in [
    (ax_top, agg_vals,
     "Aggregate (matches assessor's published figures)",
     "Σ current / Σ previous — value-weighted, all residential parcels"),
    (ax_bot, med_vals,
     "Median per parcel (typical homeowner)",
     "Median of per-parcel % changes"),
]:
    bars = ax.bar(bar_labels, vals, color=colors, width=0.5, zorder=3)
    ax.axhline(0, color="#333333", linewidth=1, zorder=2)
    ax.set_title(subtitle, fontsize=11, color="#555555", pad=8)
    ax.set_ylabel("% Change", fontsize=11)
    ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda v, _: f"{v:+.0f}%"))
    ax.grid(axis="y", color="#dddddd", zorder=1)
    ax.set_axisbelow(True)
    ax.tick_params(axis="x", labelsize=12)
    ax.spines[["top", "right", "left"]].set_visible(False)
    ax.tick_params(left=False)
    max_abs = max(abs(v) for v in vals) or 1
    thresh = 0.22 * max_abs
    for bar, val in zip(bars, vals):
        bx = bar.get_x() + bar.get_width() / 2
        if abs(val) < 0.5:
            label_y, va, col = max_abs * 0.08, "bottom", "#222222"
        elif abs(val) < thresh:
            label_y, va, col = val / 2, "center", "white"
        else:
            pad = 0.3 if val >= 0 else -0.3
            label_y = val + pad
            va = "bottom" if val >= 0 else "top"
            col = "#222222"
        ax.text(bx, label_y, f"{val:+.1f}%",
                ha="center", va=va,
                fontsize=12, fontweight="bold", color=col)
    ax.annotate(note, xy=(0.5, -0.20), xycoords="axes fraction",
                ha="center", fontsize=9, color="#777777")

fig8.tight_layout(h_pad=4.0)
fig8.savefig(os.path.join(CHARTS_DIR, "residential_aggregate_vs_median.png"), dpi=150, bbox_inches="tight")
print("Saved residential_aggregate_vs_median.png")

# ---------------------------------------------------------------------------
# Figure 9: Aggregate vs. Median — All / Improved / Vacant (stacked, mobile-friendly)
# ---------------------------------------------------------------------------
lot_labels  = ["All\nResidential", "Improved\nLots", "Vacant\nLots"]
lot_colors9 = ["#9B6BAE", "#4C8BE0", "#E07B4C"]

improved = df[df["lot_type"] == "Improved"]
vacant   = df[df["lot_type"] == "Vacant"]

def agg_total_pct(sub):
    return (sub["CurrentTotal"].sum() - sub["PreviousTotal"].sum()) / sub["PreviousTotal"].sum() * 100

agg_lot_vals = [agg_total_pct(df), agg_total_pct(improved), agg_total_pct(vacant)]
med_lot_vals = [
    df["total_pct"].median(),
    improved["total_pct"].median(),
    vacant["total_pct"].median(),
]

fig9, (ax9_top, ax9_bot) = plt.subplots(2, 1, figsize=(6, 10), sharey=False)
fig9.suptitle("Total Value Change: All / Improved / Vacant\nCurrent vs. Previous", fontsize=16, fontweight="bold")

for ax, vals, subtitle, note in [
    (ax9_top, agg_lot_vals,
     "Aggregate (value-weighted)",
     "Σ current / Σ previous — each group summed independently"),
    (ax9_bot, med_lot_vals,
     "Median per parcel (typical parcel in each group)",
     "Median of per-parcel % changes"),
]:
    bars = ax.bar(lot_labels, vals, color=lot_colors9, width=0.5, zorder=3)
    ax.axhline(0, color="#333333", linewidth=1, zorder=2)
    ax.set_title(subtitle, fontsize=11, color="#555555", pad=8)
    ax.set_ylabel("% Change in Total Value", fontsize=11)
    ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda v, _: f"{v:+.0f}%"))
    ax.grid(axis="y", color="#dddddd", zorder=1)
    ax.set_axisbelow(True)
    ax.tick_params(axis="x", labelsize=12)
    ax.spines[["top", "right", "left"]].set_visible(False)
    ax.tick_params(left=False)
    for bar, val in zip(bars, vals):
        bx = bar.get_x() + bar.get_width() / 2
        pad = 0.3 if val >= 0 else -0.3
        va = "bottom" if val >= 0 else "top"
        ax.text(bx, val + pad, f"{val:+.1f}%",
                ha="center", va=va,
                fontsize=12, fontweight="bold", color="#222222")
    ax.set_xlabel(note, fontsize=9, color="#777777", labelpad=8)

fig9.tight_layout(h_pad=4.0)
fig9.savefig(os.path.join(CHARTS_DIR, "residential_lot_type_aggregate_vs_median.png"), dpi=150, bbox_inches="tight")
print("Saved residential_lot_type_aggregate_vs_median.png")

plt.show()
print("Done.")
