from __future__ import annotations

import csv
import gzip
from pathlib import Path

import pandas as pd

from odte_lab.providers.base import Provider, ProviderCoverage, _count_files, _latest_name, _to_timestamp, read_rows


class ThetaProvider(Provider):
    def inspect(self) -> ProviderCoverage:
        paths = {
            "underlying_cache": bool(self.cfg.underlying_cache and Path(self.cfg.underlying_cache).exists()),
            "quote_dir": bool(self.cfg.quote_dir and Path(self.cfg.quote_dir).exists()),
            "tradequote_dir": bool(self.cfg.tradequote_dir and Path(self.cfg.tradequote_dir).exists()),
            "first_order_dir": bool(self.cfg.first_order_dir and Path(self.cfg.first_order_dir).exists()),
            "open_interest_dir": bool(self.cfg.open_interest_dir and Path(self.cfg.open_interest_dir).exists()),
        }
        latest = {
            "underlying_cache": Path(self.cfg.underlying_cache).name if paths["underlying_cache"] else "",
            "quote_dir": _latest_name(self.cfg.quote_dir),
            "tradequote_dir": _latest_name(self.cfg.tradequote_dir),
            "first_order_dir": _latest_name(self.cfg.first_order_dir),
            "open_interest_dir": _latest_name(self.cfg.open_interest_dir),
        }
        files_checked = (
            (1 if paths["underlying_cache"] else 0)
            + _count_files(self.cfg.quote_dir)
            + _count_files(self.cfg.tradequote_dir)
            + _count_files(self.cfg.first_order_dir)
            + _count_files(self.cfg.open_interest_dir)
        )
        notes = [
            "theta_realistic is the intended high-fidelity provider mode for QQQ 0DTE research.",
            "Results from theta_realistic should not be compared directly with massive_simplified runs.",
        ]
        return ProviderCoverage(
            provider="theta",
            mode=self.cfg.mode,
            quality_tier="theta_realistic",
            files_checked=files_checked,
            paths_present=paths,
            latest_files=latest,
            notes=notes,
        )

    def load_underlying(self, start_date, end_date) -> pd.DataFrame:
        path = Path(self.cfg.underlying_cache)
        df = pd.read_csv(path, parse_dates=["timestamp"])
        df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True).dt.tz_convert(self.cfg.timezone)
        df = df.sort_values("timestamp").set_index("timestamp")
        df = df.between_time("09:30", "16:00", inclusive="both")
        df = df[df.index.dayofweek < 5]
        return df[(df.index.date >= start_date) & (df.index.date <= end_date)]

    def load_quote_day(self, day) -> pd.DataFrame:
        path = Path(self.cfg.quote_dir) / f"{day.isoformat()}_quote.csv.gz"
        rows = read_rows(path) if path.exists() else []
        if not rows:
            return pd.DataFrame()
        df = pd.DataFrame(rows)
        df["timestamp"] = _to_timestamp(df["timestamp"], self.cfg.timezone)
        df["strike"] = pd.to_numeric(df["strike"])
        df["bid"] = pd.to_numeric(df["bid"])
        df["ask"] = pd.to_numeric(df["ask"])
        if "bid_size" in df.columns:
            df["bid_size"] = pd.to_numeric(df["bid_size"])
        if "ask_size" in df.columns:
            df["ask_size"] = pd.to_numeric(df["ask_size"])
        df["right"] = df["right"].str.upper()
        return df.sort_values(["timestamp", "right", "strike"]).reset_index(drop=True)

    def load_first_order_day(self, day) -> pd.DataFrame | None:
        if not self.cfg.first_order_dir:
            return None
        path = Path(self.cfg.first_order_dir) / f"{day.isoformat()}_first_order.csv.gz"
        rows = read_rows(path) if path.exists() else []
        if not rows:
            return None
        df = pd.DataFrame(rows)
        df["timestamp"] = _to_timestamp(df["timestamp"], self.cfg.timezone)
        df["strike"] = pd.to_numeric(df["strike"])
        df["bid"] = pd.to_numeric(df["bid"], errors="coerce")
        df["ask"] = pd.to_numeric(df["ask"], errors="coerce")
        if "delta" in df.columns:
            df["delta"] = pd.to_numeric(df["delta"], errors="coerce")
        df["right"] = df["right"].str.upper()
        return df.sort_values(["timestamp", "right", "strike"]).reset_index(drop=True)

    def load_open_interest_day(self, day) -> pd.DataFrame | None:
        if not self.cfg.open_interest_dir:
            return None
        path = Path(self.cfg.open_interest_dir) / f"{day.isoformat()}_open_interest.csv.gz"
        rows = read_rows(path) if path.exists() else []
        if not rows:
            return None
        df = pd.DataFrame(rows)
        if "timestamp" in df.columns:
            df["timestamp"] = _to_timestamp(df["timestamp"], self.cfg.timezone)
        df["strike"] = pd.to_numeric(df["strike"])
        df["open_interest"] = pd.to_numeric(df["open_interest"])
        df["right"] = df["right"].str.upper()
        return df.groupby(["right", "strike"], as_index=False)["open_interest"].last()

    def load_tradequote_day(self, day, right: str, strike: float) -> pd.DataFrame | None:
        if not self.cfg.tradequote_dir:
            return None
        path = Path(self.cfg.tradequote_dir) / f"{day.isoformat()}_trade_quote.csv.gz"
        rows: list[dict[str, str]] = []
        if path.exists():
            with gzip.open(path, "rt", encoding="utf-8", newline="") as fh:
                reader = csv.DictReader(fh)
                for row in reader:
                    if str(row["right"]).upper() != right.upper():
                        continue
                    if float(row["strike"]) != float(strike):
                        continue
                    rows.append(row)
        if not rows:
            return None
        df = pd.DataFrame(rows)
        df["right"] = df["right"].str.upper()
        df["strike"] = pd.to_numeric(df["strike"])
        df = df[(df["right"] == right.upper()) & (df["strike"] == float(strike))].copy()
        if df.empty:
            return None
        df["quote_timestamp"] = _to_timestamp(df["quote_timestamp"], self.cfg.timezone)
        df["trade_timestamp"] = _to_timestamp(df["trade_timestamp"], self.cfg.timezone)
        df["bid"] = pd.to_numeric(df["bid"])
        df["ask"] = pd.to_numeric(df["ask"])
        return df.sort_values(["quote_timestamp", "trade_timestamp"]).reset_index(drop=True)
