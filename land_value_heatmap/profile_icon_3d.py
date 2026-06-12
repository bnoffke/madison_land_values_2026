import os
from pathlib import Path

import geopandas as gpd
import matplotlib.cm as mcm
import matplotlib.colors as mcolors
import matplotlib
import numpy as np
import pandas as pd
import pydeck as pdk
from playwright.sync_api import sync_playwright
from pyproj import Transformer

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
CHARTS_DIR = os.path.join(SCRIPT_DIR, "charts")
os.makedirs(CHARTS_DIR, exist_ok=True)

# --- Tunable parameters ---
ELEVATION_SCALE = 22     # visual height multiplier
CELL_M = 100             # grid cell size in meters
RADIUS = 48              # column half-width in meters (slightly less than cell for gaps)
PITCH = 45               # camera tilt (0=top-down, 90=horizontal)
BEARING = 0              # north-up, no rotation
ZOOM = 11.8              # map zoom level
HEIGHT_CAP_PCT = 98      # clip outliers at this percentile for height
COLOR_CAP_PCT = 98       # clip for color mapping
CMAP = "magma_r"
VIEWPORT_PX = 900        # square output size

# Wider bbox to show value gradient from downtown → outskirts
LON_MIN, LON_MAX = -89.46, -89.32
LAT_MIN, LAT_MAX = 43.040, 43.110
CENTER_LON, CENTER_LAT = -89.384, 43.068

print("Loading GeoJSON...")
gdf_full = gpd.read_file(
    os.path.join(SCRIPT_DIR, "..", "Tax_Parcels.geojson"), engine="pyogrio"
)

# Aggregate condos to master parcel (all property classes)
agg = gdf_full.groupby("XRefParcel", as_index=False).agg(
    CurrentLand=("CurrentLand", "sum"),
)
master = gdf_full[["Parcel", "LotSize", "geometry"]].rename(columns={"Parcel": "XRefParcel"})
merged = agg.merge(master, on="XRefParcel", how="left")
merged = gpd.GeoDataFrame(merged, geometry="geometry").set_crs("EPSG:4326").to_crs("EPSG:3857")

# Fill zero/missing LotSize from geometry area (sq m → sq ft)
zero_mask = merged["LotSize"].isna() | (merged["LotSize"] == 0)
merged.loc[zero_mask, "LotSize"] = merged.loc[zero_mask].geometry.area * 10.7639
print(f"  Filled {zero_mask.sum()} zero-LotSize parcels from geometry")

merged["land_sqft_2026"] = np.where(
    (merged["LotSize"] > 0) & (merged["CurrentLand"] > 0),
    merged["CurrentLand"] / merged["LotSize"],
    np.nan,
)

# Filter to bbox
tf_fwd = Transformer.from_crs("EPSG:4326", "EPSG:3857", always_xy=True)
x_min, y_min = tf_fwd.transform(LON_MIN, LAT_MIN)
x_max, y_max = tf_fwd.transform(LON_MAX, LAT_MAX)

cx = merged.geometry.centroid.x
cy = merged.geometry.centroid.y
bbox_mask = (cx >= x_min) & (cx <= x_max) & (cy >= y_min) & (cy <= y_max)
gdf = merged[bbox_mask & merged["land_sqft_2026"].notna()].copy()
print(f"  Parcels in bbox: {len(gdf):,}")

# --- Grid aggregation ---
cx_arr = gdf.geometry.centroid.x.values
cy_arr = gdf.geometry.centroid.y.values
vals = gdf["land_sqft_2026"].values

cols = ((cx_arr - x_min) / CELL_M).astype(int)
rows = ((cy_arr - y_min) / CELL_M).astype(int)
n_cols = int((x_max - x_min) / CELL_M) + 1
n_rows = int((y_max - y_min) / CELL_M) + 1

grid_sum = np.zeros((n_rows, n_cols))
grid_cnt = np.zeros((n_rows, n_cols))
for c, r, v in zip(cols, rows, vals):
    if 0 <= r < n_rows and 0 <= c < n_cols:
        grid_sum[r, c] += v
        grid_cnt[r, c] += 1

with np.errstate(invalid="ignore"):
    grid_mean = np.where(grid_cnt > 0, grid_sum / grid_cnt, np.nan)

bar_rows, bar_cols = np.where(~np.isnan(grid_mean))
bar_vals = grid_mean[bar_rows, bar_cols]

# Convert cell centers back to WGS84 for pydeck
tf_rev = Transformer.from_crs("EPSG:3857", "EPSG:4326", always_xy=True)
bar_x_m = x_min + (bar_cols + 0.5) * CELL_M
bar_y_m = y_min + (bar_rows + 0.5) * CELL_M
bar_lon, bar_lat = tf_rev.transform(bar_x_m, bar_y_m)

print(f"  Grid cells with data: {len(bar_vals):,}")

# --- Color mapping ---
color_cap = np.nanpercentile(bar_vals, COLOR_CAP_PCT)
norm = mcolors.Normalize(vmin=np.nanpercentile(bar_vals, 2), vmax=color_cap)
cmap = matplotlib.colormaps[CMAP]
rgba = cmap(norm(bar_vals))
r_col = (rgba[:, 0] * 255).astype(int)
g_col = (rgba[:, 1] * 255).astype(int)
b_col = (rgba[:, 2] * 255).astype(int)

# Cap heights separately
height_cap = np.nanpercentile(bar_vals, HEIGHT_CAP_PCT)
bar_elev = np.minimum(bar_vals, height_cap)

df = pd.DataFrame({
    "lon": bar_lon,
    "lat": bar_lat,
    "elevation": bar_elev,
    "r": r_col,
    "g": g_col,
    "b": b_col,
})

# --- pydeck ---
layer = pdk.Layer(
    "ColumnLayer",
    data=df,
    get_position=["lon", "lat"],
    get_elevation="elevation",
    elevation_scale=ELEVATION_SCALE,
    radius=RADIUS,
    get_fill_color=["r", "g", "b", 230],
    extruded=True,
    coverage=1.0,
    pickable=False,
)

view = pdk.ViewState(
    longitude=CENTER_LON,
    latitude=CENTER_LAT,
    zoom=ZOOM,
    pitch=PITCH,
    bearing=BEARING,
)

deck = pdk.Deck(
    layers=[layer],
    initial_view_state=view,
    map_style="https://basemaps.cartocdn.com/gl/positron-nolabels-gl-style/style.json",
)

html_path = Path(CHARTS_DIR) / "profile_icon_3d_tmp.html"
png_path = Path(CHARTS_DIR) / "profile_icon_3d.png"

deck.to_html(str(html_path), notebook_display=False)
print(f"  Wrote HTML to {html_path}")

# --- Screenshot ---
print("Screenshotting with playwright...")
with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page(viewport={"width": VIEWPORT_PX, "height": VIEWPORT_PX})
    page.goto(html_path.resolve().as_uri())
    page.wait_for_timeout(6000)   # let tiles + WebGL finish rendering
    page.screenshot(path=str(png_path))
    browser.close()

print(f"Saved {png_path}")
