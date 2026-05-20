"""Folium interactive station map for Mumbai local dashboard."""
import folium
import polars as pl

_MUMBAI_CENTER = [19.0760, 72.8777]

_LINE_COLORS = {
    "Central": "#E63946",
    "Western": "#457B9D",
    "Harbour": "#2A9D8F",
}

_DELAY_THRESHOLDS = [
    (2.0, "green"),
    (5.0, "orange"),
    (float("inf"), "red"),
]


def _delay_color(avg_delay: float) -> str:
    for threshold, color in _DELAY_THRESHOLDS:
        if avg_delay <= threshold:
            return color
    return "red"


def make_station_map(
    stops: pl.DataFrame,
    delay_today: pl.DataFrame | None = None,
) -> str:
    """Build a Folium station map and return HTML string."""
    m = folium.Map(
        location=_MUMBAI_CENTER,
        zoom_start=11,
        tiles="CartoDB positron",
    )

    delay_map: dict[str, float] = {}
    if delay_today is not None:
        for row in delay_today.iter_rows(named=True):
            delay_map[row["station_name"]] = row["avg_delay"]

    for row in stops.iter_rows(named=True):
        station = row["station_name"]
        lat = row.get("stop_lat", 0.0)
        lon = row.get("stop_lon", 0.0)
        line = row.get("line", "Unknown")
        avg_delay = delay_map.get(station, 0.0)
        color = _delay_color(avg_delay)

        popup_html = f"""
        <b>{station}</b><br>
        Line: {line}<br>
        Avg delay today: <b>{avg_delay:.1f} min</b>
        """

        folium.CircleMarker(
            location=[lat, lon],
            radius=8,
            color="#333",
            weight=1,
            fill=True,
            fill_color=color,
            fill_opacity=0.9,
            popup=folium.Popup(popup_html, max_width=200),
            tooltip=f"{station}: {avg_delay:.1f} min",
        ).add_to(m)

    legend_html = """
    <div style="position: fixed; bottom: 30px; left: 30px; z-index: 1000;
                background: #1a1a2e; padding: 10px; border-radius: 8px;
                color: white; font-family: Inter;">
      <b>Delay Severity</b><br>
      Green: <=2 min (on time)<br>
      Orange: 2-5 min (minor)<br>
      Red: >5 min (severe)
    </div>
    """
    m.get_root().html.add_child(folium.Element(legend_html))  # type: ignore[attr-defined]

    return m._repr_html_()
