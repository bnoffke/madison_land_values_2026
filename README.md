# madison_land_values_2026
Analyzing land values from 2026 assessments.
Contains code to generate graphs for Substack post.

This includes a script to download the assessor data as current, which means it could change as the assessor makes changes based on assessment challenges or parcel changes.
The larger historical trend data comes from the tax roll data, which I've compiled via my own ingestion and dbt project and query with duckdb (via a conveniece script called duckquery). 