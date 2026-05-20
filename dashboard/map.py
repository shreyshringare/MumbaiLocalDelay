"""Folium interactive station map for Mumbai local dashboard."""
import folium
import polars as pl

_MUMBAI_CENTER = [19.0760, 72.8777]

_DELAY_THRESHOLDS = [
    (2.0, "green"),
    (5.0, "orange"),
    (float("inf"), "red"),
]

_LEGEND_COLORS = {
    "green":  "#2A9D8F",
    "orange": "#E9C46A",
    "red":    "#E63946",
}


def _delay_color(avg_delay: float) -> str:
    for threshold, color in _DELAY_THRESHOLDS:
        if avg_delay <= threshold:
            return color
    return "red"


def make_station_map(
    stops: pl.DataFrame,
    delay_data: pl.DataFrame | None = None,
) -> str:
    """Build a Folium station map coloured by all-time avg delay. Return HTML string.

    Args:
        stops: DataFrame with columns [station_name, stop_lat, stop_lon, line]
        delay_data: DataFrame with columns [station_name, avg_delay, min_delay,
                    max_delay, days_observed]. If None, markers are grey.
    """
    m = folium.Map(
        location=_MUMBAI_CENTER,
        zoom_start=11,
        tiles="CartoDB dark_matter",
    )

    # Build lookup: station_name → delay stats row
    stats: dict[str, dict] = {}
    if delay_data is not None:
        for row in delay_data.iter_rows(named=True):
            stats[row["station_name"]] = row

    for row in stops.iter_rows(named=True):
        station = row["station_name"]
        lat = row.get("stop_lat", 0.0)
        lon = row.get("stop_lon", 0.0)
        line = row.get("line", "Unknown")
        s = stats.get(station, {})
        avg_delay = s.get("avg_delay", 0.0) or 0.0
        min_delay = s.get("min_delay", 0.0) or 0.0
        max_delay = s.get("max_delay", 0.0) or 0.0
        days = s.get("days_observed", 0) or 0
        color = _delay_color(avg_delay)

        popup_html = (
            f"<div style='font-family:Inter,sans-serif;min-width:160px'>"
            f"<b style='font-size:13px'>{station}</b><br>"
            f"<span style='color:#888'>Line: {line}</span><br><hr style='margin:4px 0'>"
            f"Avg delay: <b>{avg_delay:.1f} min</b><br>"
            f"Range: {min_delay:.1f} – {max_delay:.1f} min<br>"
            f"Observed: {days} days"
            f"</div>"
        )

        folium.CircleMarker(
            location=[lat, lon],
            radius=7,
            color="#222",
            weight=1,
            fill=True,
            fill_color=_LEGEND_COLORS.get(color, color),
            fill_opacity=0.85,
            popup=folium.Popup(popup_html, max_width=220),
            tooltip=f"{station} · {avg_delay:.1f} min avg",
        ).add_to(m)

    legend_html = """
    <div style="position:fixed;bottom:30px;left:30px;z-index:1000;
                background:rgba(22,33,62,0.95);padding:12px 16px;
                border-radius:8px;color:#eaeaea;font-family:Inter,sans-serif;font-size:12px">
      <b style="font-size:13px">Avg Delay (2-yr history)</b><br><br>
      <span style="color:#2A9D8F">&#9679;</span> &le;2 min &nbsp;(on time)<br>
      <span style="color:#E9C46A">&#9679;</span> 2&ndash;5 min (minor)<br>
      <span style="color:#E63946">&#9679;</span> &gt;5 min &nbsp;(severe)
    </div>
    """
    m.get_root().html.add_child(folium.Element(legend_html))  # type: ignore[attr-defined]

    return m._repr_html_()
