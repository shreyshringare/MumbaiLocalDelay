"""Pydantic v2 response models for the Mumbai Local Delay API."""

from pydantic import BaseModel, ConfigDict


class StationDelay(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    station_name: str
    line: str
    avg_delay: float
    latitude: float | None
    longitude: float | None


class HeatmapResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    station: str
    matrix: list[list[float | None]]


class RankingEntry(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    station_name: str
    line: str
    avg_delay: float
    ci_lower: float | None
    ci_upper: float | None


class AnomalyEntry(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    station: str
    severity: str
    actual: float
    expected: float
    upper: float
    date: str


class LineTrendPoint(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    date: str
    line: str
    avg_delay: float


class QualityEntry(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    station_name: str
    row_count: int
    unique_dates: int
    last_updated: str | None


class InsightsResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    worst_station: str
    worst_delay: float
    best_line: str
    best_line_delay: float
    peak_window: str
    delay_hours_per_day: float
    commuters_affected: str


class ForecastPoint(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    ds: str
    yhat: float
    yhat_lower: float
    yhat_upper: float
