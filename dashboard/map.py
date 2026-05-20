"""Folium interactive station map for Mumbai local dashboard.

Renders two layers:
  1. HeatMap gradient — delay intensity surface (green→yellow→red)
  2. CircleMarker per station — clickable detail popup
"""
import folium
import polars as pl
from folium.plugins import HeatMap

_MUMBAI_CENTER = [19.0760, 72.8777]

_DELAY_THRESHOLDS = [
    (2.0, "#2A9D8F"),   # teal  — on time
    (5.0, "#E9C46A"),   # amber — minor
    (float("inf"), "#E63946"),  # red — severe
]


def _marker_color(avg_delay: float) -> str:
    for threshold, color in _DELAY_THRESHOLDS:
        if avg_delay <= threshold:
            return color
    return "#E63946"


def make_station_map(
    stops: pl.DataFrame,
    delay_data: pl.DataFrame | None = None,
) -> str:
    """Build a Folium gradient heatmap + station markers. Return HTML string.

    Args:
        stops: DataFrame with columns [station_name, latitude, longitude, line]
        delay_data: DataFrame with columns [station_name, avg_delay, min_delay,
                    max_delay, days_observed]. If None, markers show without color.
    """
    m = folium.Map(
        location=_MUMBAI_CENTER,
        zoom_start=11,
        tiles="CartoDB dark_matter",
    )

    # Build lookup: station_name → stats dict
    stats: dict[str, dict] = {}
    if delay_data is not None:
        for row in delay_data.iter_rows(named=True):
            stats[row["station_name"]] = row

    # --- Layer 1: HeatMap gradient ---
    # Weight = avg_delay so high-delay stations glow red
    heat_points: list[list[float]] = []
    for row in stops.iter_rows(named=True):
        lat = row.get("latitude", row.get("stop_lat", 0.0)) or 0.0
        lon = row.get("longitude", row.get("stop_lon", 0.0)) or 0.0
        if lat == 0.0 and lon == 0.0:
            continue
        s = stats.get(row["station_name"], {})
        weight = s.get("avg_delay", 1.0) or 1.0
        heat_points.append([lat, lon, weight])

    if heat_points:
        HeatMap(
            heat_points,
            radius=35,
            blur=25,
            min_opacity=0.35,
            max_zoom=13,
            gradient={0.0: "green", 0.5: "yellow", 1.0: "red"},
        ).add_to(m)

    # --- Layer 2: CircleMarker per station (click for detail) ---
    for row in stops.iter_rows(named=True):
        station = row["station_name"]
        lat = row.get("latitude", row.get("stop_lat", 0.0)) or 0.0
        lon = row.get("longitude", row.get("stop_lon", 0.0)) or 0.0
        if lat == 0.0 and lon == 0.0:
            continue
        line = row.get("line", "Unknown")
        s = stats.get(station, {})
        avg_delay = s.get("avg_delay", 0.0) or 0.0
        min_delay = s.get("min_delay", 0.0) or 0.0
        max_delay = s.get("max_delay", 0.0) or 0.0
        days = s.get("days_observed", 0) or 0

        popup_html = (
            f"<div style='font-family:Inter,sans-serif;min-width:170px'>"
            f"<b style='font-size:13px'>{station}</b><br>"
            f"<span style='color:#888;font-size:11px'>Line: {line}</span>"
            f"<hr style='margin:5px 0;border-color:#333'>"
            f"Avg delay: <b style='color:#E63946'>{avg_delay:.1f} min</b><br>"
            f"Range: {min_delay:.1f} – {max_delay:.1f} min<br>"
            f"<span style='color:#888;font-size:11px'>Observed over {days} days</span>"
            f"</div>"
        )

        folium.CircleMarker(
            location=[lat, lon],
            radius=5,
            color="#111",
            weight=1,
            fill=True,
            fill_color=_marker_color(avg_delay),
            fill_opacity=0.9,
            popup=folium.Popup(popup_html, max_width=220),
            tooltip=f"{station} · {avg_delay:.1f} min",
        ).add_to(m)

    # --- Legend ---
    legend_html = """
    <div style="position:fixed;bottom:30px;left:30px;z-index:1000;
                background:rgba(22,33,62,0.92);padding:12px 16px;
                border-radius:8px;color:#eaeaea;font-family:Inter,sans-serif;font-size:12px;
                border:1px solid rgba(255,255,255,0.08)">
      <b style="font-size:13px">Avg Delay &mdash; 2-yr history</b><br><br>
      <span style="color:#2A9D8F">&#9679;</span>&nbsp;&le;2 min&nbsp;&nbsp;(on time)<br>
      <span style="color:#E9C46A">&#9679;</span>&nbsp;2&ndash;5 min&nbsp;(minor)<br>
      <span style="color:#E63946">&#9679;</span>&nbsp;&gt;5 min&nbsp;&nbsp;&nbsp;(severe)<br><br>
      <span style="color:#888;font-size:11px">Heatmap intensity = delay magnitude<br>
      Click any station for full stats</span>
    </div>
    """
    m.get_root().html.add_child(folium.Element(legend_html))  # type: ignore[attr-defined]

    return m._repr_html_()
