We're analyzing land value changes from the city of Madison assessor's office. This will be used to inform a substack article. The goal is to highlight accurate land valuation as a step toward Georgism.

Use uv for python:
- `uv run ...` to run any script
- `uv add ...` to add any packages
- `uv sync ...` to build env

## Chart Standards

### Color palette (use consistently across all charts)

| Series | Hex |
|---|---|
| Land value | `#6AAB6A` (green — land/grass) |
| Improvement value | `#5B8DB8` (blue) |
| Total value | `#9B6BAE` (purple) |
| Improved lots | `#4C8BE0` (brighter blue) |
| Vacant lots | `#E07B4C` (orange) |
| All Residential | `#9B6BAE` (same as Total) |
| Muted prior-year land bars | `#c8e6c8` (light green) |
| Secondary land line (gorham vacant) | `#a8d9a8` (lighter green, dashed) |

Exception: `gorham_trend_v1_overlay.png` uses two greens to distinguish two properties' land values — specialized scheme, keep as-is.

### Mobile sizing (portrait/square, max ~7" wide)

| Chart type | figsize |
|---|---|
| Line trend (1 panel) | `(6, 7)` |
| Bar chart (3–4 bars) | `(6, 6)` or `(6, 7)` |
| Stacked 2-panel bar | `(6, 10)` |
| Box plot (3 boxes, side-by-side) | `(7, 6)` |
| Box plot (4 boxes, side-by-side) | `(7, 7)` |

- Avoid `sharey=True` across panels when the data ranges differ significantly (e.g., one panel has a +79% bar and the other tops at +18%).