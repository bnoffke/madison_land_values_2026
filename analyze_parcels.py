import geopandas as gpd
import pandas as pd
import numpy as np
import seaborn as sns
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker

# ---------------------------------------------------------------------------
# Load & prepare
# ---------------------------------------------------------------------------
print("Loading GeoJSON...")
gdf = gpd.read_file("Tax_Parcels.geojson", engine="pyogrio")

cols = [
    "PropertyClass", "PropertyUse",
    "CurrentLand", "PreviousLand",
    "CurrentImpr", "PreviousImpr",
    "CurrentTotal", "PreviousTotal",
]
df = gdf[cols].copy()
total_current_all = df["CurrentTotal"].sum()
total_prev_all    = df["PreviousTotal"].sum()

# Percentage change; rows with $0 previous become NaN (dropped by seaborn)
def pct_chg(curr, prev):
    return np.where(prev != 0, (curr - prev) / prev * 100.0, np.nan)

df["land_pct"]  = pct_chg(df["CurrentLand"],  df["PreviousLand"])
df["impr_pct"]  = pct_chg(df["CurrentImpr"],  df["PreviousImpr"])
df["total_pct"] = pct_chg(df["CurrentTotal"], df["PreviousTotal"])

df["is_vacant"] = df["PropertyUse"].str.lower().str.contains("vacant", na=False)
df["lot_type"]  = df["is_vacant"].map({True: "Vacant", False: "Improved"})

# Keep the four meaningful property classes
keep_classes = ["Residential", "Commercial"]
df = df[df["PropertyClass"].isin(keep_classes)].copy()
df["PropertyClass"] = pd.Categorical(df["PropertyClass"], categories=keep_classes, ordered=True)

df["current_share"] = df["CurrentTotal"] / total_current_all
df["prev_share"]    = df["PreviousTotal"] / total_prev_all
df["share_pct"]     = np.where(
    df["prev_share"] > 0,
    (df["current_share"] - df["prev_share"]) / df["prev_share"] * 100,
    np.nan,
)

print(f"Records after filtering: {len(df):,}")
print("\nVacant lot counts by class:")
print(df[df["is_vacant"]].groupby("PropertyClass", observed=True).size().to_string())

# ---------------------------------------------------------------------------
# Shared plot settings
# ---------------------------------------------------------------------------
sns.set_theme(style="whitegrid", palette="muted")
FLIER = dict(marker="o", markersize=2, alpha=0.25, linestyle="none")
MEDIAN_PROPS = dict(color="black", linewidth=1.5)

# ---------------------------------------------------------------------------
# Figure 1: Land / Improvement / Total % change by property class
# ---------------------------------------------------------------------------
metrics = [
    ("land_pct",  "Land Value % Change"),
    ("impr_pct",  "Improvement Value % Change"),
    ("total_pct", "Total Value % Change"),
]

fig1, axes1 = plt.subplots(1, 3, figsize=(18, 7), sharey=False)
fig1.suptitle("Assessment % Change by Property Class\n(Current vs. Previous)", fontsize=14, y=1.01)

for ax, (col, title) in zip(axes1, metrics):
    plot_df = df[["PropertyClass", col]].dropna(subset=[col])

    # Cap extreme outliers for visual clarity (keep within 1st–99th pct per class)
    lo = plot_df[col].quantile(0.01)
    hi = plot_df[col].quantile(0.99)
    plot_df = plot_df[(plot_df[col] >= lo) & (plot_df[col] <= hi)]

    sns.boxplot(
        data=plot_df,
        x="PropertyClass",
        y=col,
        order=keep_classes,
        flierprops=FLIER,
        medianprops=MEDIAN_PROPS,
        width=0.5,
        ax=ax,
    )
    ax.axhline(0, color="red", linewidth=1, linestyle="--", alpha=0.7)
    ax.set_title(title, fontsize=11)
    ax.set_xlabel("")
    ax.set_ylabel("% Change" if ax == axes1[0] else "")
    ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda v, _: f"{v:+.0f}%"))
    ax.tick_params(axis="x", rotation=20)

    # Annotate median value on each box
    medians = plot_df.groupby("PropertyClass", observed=True)[col].median()
    for i, cls in enumerate(keep_classes):
        if cls in medians.index:
            ax.text(
                i, medians[cls],
                f"{medians[cls]:+.1f}%",
                ha="center", va="bottom", fontsize=7.5, color="black", fontweight="bold",
            )

fig1.text(
    0.5, -0.02,
    "Whiskers = 1.5×IQR  |  Outliers trimmed to 1st–99th percentile per metric",
    ha="center", fontsize=9, color="gray"
)
fig1.tight_layout()
fig1.savefig("assessment_change_by_class.png", dpi=150, bbox_inches="tight")
print("Saved assessment_change_by_class.png")

# ---------------------------------------------------------------------------
# Figure 2: Vacant vs Improved — total % change by property class
# ---------------------------------------------------------------------------
fig2, ax2 = plt.subplots(figsize=(12, 7))
fig2.suptitle(
    "Total Value % Change: Vacant vs. Improved Lots by Property Class\n(Current vs. Previous)",
    fontsize=14,
)

plot_df2 = df[["PropertyClass", "lot_type", "total_pct"]].dropna(subset=["total_pct"])
lo2 = plot_df2["total_pct"].quantile(0.01)
hi2 = plot_df2["total_pct"].quantile(0.99)
plot_df2 = plot_df2[(plot_df2["total_pct"] >= lo2) & (plot_df2["total_pct"] <= hi2)]

palette = {"Improved": "#4C8BE0", "Vacant": "#E07B4C"}

sns.boxplot(
    data=plot_df2,
    x="PropertyClass",
    y="total_pct",
    hue="lot_type",
    hue_order=["Improved", "Vacant"],
    order=keep_classes,
    palette=palette,
    flierprops=FLIER,
    medianprops=MEDIAN_PROPS,
    width=0.6,
    ax=ax2,
)
ax2.axhline(0, color="red", linewidth=1, linestyle="--", alpha=0.7)
ax2.set_xlabel("Property Class", fontsize=11)
ax2.set_ylabel("Total Value % Change", fontsize=11)
ax2.yaxis.set_major_formatter(mticker.FuncFormatter(lambda v, _: f"{v:+.0f}%"))
ax2.tick_params(axis="x", rotation=15)
ax2.legend(title="Lot Type", loc="upper right")

# Annotate n= counts above each group
counts = plot_df2.groupby(["PropertyClass", "lot_type"], observed=True).size()
n_classes = len(keep_classes)
box_width = 0.6
group_gap = 1.0
n_hue = 2
offsets = [-box_width / 4, box_width / 4]

y_top = ax2.get_ylim()[1]

for i, cls in enumerate(keep_classes):
    for j, lot in enumerate(["Improved", "Vacant"]):
        n = counts.get((cls, lot), 0)
        x_pos = i + offsets[j]
        ax2.text(
            x_pos, y_top * 0.97,
            f"n={n:,}",
            ha="center", va="top", fontsize=7.5, color="gray",
        )

fig2.text(
    0.5, -0.02,
    "Whiskers = 1.5×IQR  |  Outliers trimmed to 1st–99th percentile",
    ha="center", fontsize=9, color="gray"
)
fig2.tight_layout()
fig2.savefig("vacant_vs_improved_by_class.png", dpi=150, bbox_inches="tight")
print("Saved vacant_vs_improved_by_class.png")

# ---------------------------------------------------------------------------
# Figure 3: Tax share delta by property class (box/whisker)
# ---------------------------------------------------------------------------
palette3 = {
    "Residential": "#5B8DB8",
    "Commercial":  "#E07B4C",
}

plot3 = df[["PropertyClass", "share_pct"]].copy()
lo3, hi3 = plot3["share_pct"].quantile(0.02), plot3["share_pct"].quantile(0.98)
plot3["share_pct"] = plot3["share_pct"].clip(lo3, hi3)
plot3 = plot3.dropna(subset=["share_pct"])

fig3, ax3 = plt.subplots(figsize=(10, 7))
fig3.suptitle(
    "Tax Share Change by Property Class\n(Current vs. Previous)",
    fontsize=14,
)

sns.boxplot(
    data=plot3,
    x="PropertyClass",
    y="share_pct",
    hue="PropertyClass",
    order=keep_classes,
    palette=palette3,
    flierprops=FLIER,
    medianprops=MEDIAN_PROPS,
    width=0.5,
    legend=False,
    ax=ax3,
)
ax3.axhline(0, color="red", linewidth=1, linestyle="--", alpha=0.7)
ax3.set_xlabel("")
ax3.set_ylabel("Share Change (%)", fontsize=11)
ax3.yaxis.set_major_formatter(mticker.FuncFormatter(lambda v, _: f"{v:+.0f}%"))

counts3 = plot3.groupby("PropertyClass", observed=True)["share_pct"].count()
ax3.set_xticks(range(len(keep_classes)))
ax3.set_xticklabels([
    f"{cls}\n(n={counts3.get(cls, 0):,})" for cls in keep_classes
], fontsize=10)

fig3.text(
    0.5, -0.02,
    "Positive = class now bears a larger share of the levy  |  Clipped to 2nd–98th percentile",
    ha="center", fontsize=9, color="gray",
)
fig3.tight_layout()
fig3.savefig("share_change_by_class.png", dpi=150, bbox_inches="tight")
print("Saved share_change_by_class.png")

# ---------------------------------------------------------------------------
# Figures 4 & 5: Aggregate bar charts (value % change and share % change)
# ---------------------------------------------------------------------------
class_agg = df.groupby("PropertyClass", observed=True).agg(
    current=("CurrentTotal", "sum"),
    previous=("PreviousTotal", "sum"),
).reindex(keep_classes)

class_value_pct = ((class_agg["current"] - class_agg["previous"]) / class_agg["previous"] * 100).tolist()

class_share_curr = class_agg["current"] / total_current_all
class_share_prev = class_agg["previous"] / total_prev_all
class_share_pct  = ((class_share_curr - class_share_prev) / class_share_prev * 100).tolist()

class_colors = ["#5B8DB8", "#E07B4C"]


def make_bar_chart(values, title, subtitle, ylabel, annotation):
    fig, ax = plt.subplots(figsize=(10, 6))
    fig.suptitle(title, fontsize=16, fontweight="bold", y=0.98)
    ax.set_title(subtitle, fontsize=11, color="#555555", pad=8)

    bars = ax.bar(keep_classes, values, color=class_colors, width=0.5, zorder=3)
    y_span = max(values) - min(0, min(values))
    ax.set_ylim(bottom=min(0, min(values)) - y_span * 0.4)
    ax.axhline(0, color="#333333", linewidth=1, zorder=2)
    ax.set_ylabel(ylabel, fontsize=12)
    ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda v, _: f"{v:+.0f}%"))
    ax.grid(axis="y", color="#dddddd", zorder=1)
    ax.set_axisbelow(True)
    ax.tick_params(axis="x", labelsize=12)
    ax.spines[["top", "right", "left"]].set_visible(False)
    ax.tick_params(left=False)

    for bar, val in zip(bars, values):
        pad = 0.3 if val >= 0 else -0.3
        va  = "bottom" if val >= 0 else "top"
        ax.text(
            bar.get_x() + bar.get_width() / 2,
            val + pad,
            f"{val:+.1f}%",
            ha="center", va=va,
            fontsize=13, fontweight="bold", color="#222222",
        )

    ax.annotate(
        annotation,
        xy=(0.5, -0.12), xycoords="axes fraction",
        ha="center", fontsize=9, color="#777777",
    )

    fig.tight_layout()
    return fig


fig4 = make_bar_chart(
    class_value_pct,
    title="Total Assessed Value % Change by Property Class",
    subtitle="Aggregate current vs. previous — sum of class values",
    ylabel="% Change in Total Assessed Value",
    annotation="Aggregate % change: (Σcurrent − Σprevious) / Σprevious",
)
fig4.savefig("value_change_by_class_means.png", dpi=150, bbox_inches="tight")
print("Saved value_change_by_class_means.png")

fig5 = make_bar_chart(
    class_share_pct,
    title="Tax Share % Change by Property Class",
    subtitle="Each class's share of citywide total — current vs. previous",
    ylabel="% Change in Tax Share",
    annotation="Share = Σclass / Σall properties  |  Positive = class bears a larger share of the levy",
)
fig5.savefig("share_change_by_class_means.png", dpi=150, bbox_inches="tight")
print("Saved share_change_by_class_means.png")

plt.show()
print("Done.")
