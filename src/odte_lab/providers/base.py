from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import date
import csv
import gzip
from pathlib import Path

import pandas as pd

from odte_lab.domain import DataConfig


@dataclass(frozen=True)
class ProviderCoverage:
    provider: str
    mode: str
    quality_tier: str
    files_checked: int
    paths_present: dict[str, bool]
    latest_files: dict[str, str]
    notes: list[str]

    def to_dict(self) -> dict:
        return asdict(self)


class Provider:
    def __init__(self, cfg: DataConfig):
        self.cfg = cfg

    def inspect(self) -> ProviderCoverage:
        raise NotImplementedError

    def load_underlying(self, start_date: date, end_date: date) -> pd.DataFrame:
        raise NotImplementedError

    def load_quote_day(self, day: date) -> pd.DataFrame:
        raise NotImplementedError

    def load_first_order_day(self, day: date) -> pd.DataFrame | None:
        return None

    def load_open_interest_day(self, day: date) -> pd.DataFrame | None:
        return None

    def load_tradequote_day(self, day: date, right: str, strike: float) -> pd.DataFrame | None:
        return None


def _latest_name(path: str) -> str:
    base = Path(path)
    if not path or not base.exists():
        return ""
    candidates = sorted(p.name for p in base.glob("*") if p.is_file())
    return candidates[-1] if candidates else ""


def _count_files(path: str) -> int:
    base = Path(path)
    if not path or not base.exists():
        return 0
    return sum(1 for p in base.glob("*") if p.is_file())


def read_rows(path: Path) -> list[dict[str, str]]:
    opener = gzip.open if path.suffix == ".gz" else open
    with opener(path, "rt", encoding="utf-8", newline="") as fh:
        return list(csv.DictReader(fh))


def _to_timestamp(series: pd.Series, timezone: str) -> pd.Series:
    ts = pd.to_datetime(series, utc=False, errors="coerce")
    if getattr(ts.dt, "tz", None) is None:
        return ts.dt.tz_localize(timezone)
    return ts.dt.tz_convert(timezone)


class ProviderFactory:
    @staticmethod
    def build(cfg: DataConfig) -> Provider:
        if cfg.provider == "theta":
            from odte_lab.providers.theta import ThetaProvider

            return ThetaProvider(cfg)
        if cfg.provider == "massive_file":
            from odte_lab.providers.massive import MassiveFileProvider

            return MassiveFileProvider(cfg)
        raise ValueError(f"Unsupported provider: {cfg.provider}")
