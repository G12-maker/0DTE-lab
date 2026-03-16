from __future__ import annotations

from pathlib import Path

import pandas as pd

from odte_lab.providers.base import Provider, ProviderCoverage, _count_files, _latest_name, _to_timestamp, read_rows


class MassiveFileProvider(Provider):
    def inspect(self) -> ProviderCoverage:
        paths = {
            "underlying_dir": bool(self.cfg.underlying_dir and Path(self.cfg.underlying_dir).exists()),
            "options_dir": bool(self.cfg.options_dir and Path(self.cfg.options_dir).exists()),
            "contracts_dir": bool(self.cfg.contracts_dir and Path(self.cfg.contracts_dir).exists()),
        }
        latest = {
            "underlying_dir": _latest_name(self.cfg.underlying_dir),
            "options_dir": _latest_name(self.cfg.options_dir),
            "contracts_dir": _latest_name(self.cfg.contracts_dir),
        }
        files_checked = (
            _count_files(self.cfg.underlying_dir)
            + _count_files(self.cfg.options_dir)
            + _count_files(self.cfg.contracts_dir)
        )
        notes = [
            "massive_simplified is intended for onboarding and low-friction smoke tests.",
            "massive_simplified does not imply tick-level execution fidelity.",
        ]
        return ProviderCoverage(
            provider="massive_file",
            mode=self.cfg.mode,
            quality_tier="massive_simplified",
            files_checked=files_checked,
            paths_present=paths,
            latest_files=latest,
            notes=notes,
        )

    def _candidate(self, base: str, day, suffixes: tuple[str, ...]) -> Path | None:
        root = Path(base)
        for suffix in suffixes:
            path = root / f"{day.isoformat()}{suffix}"
            if path.exists():
                return path
        return None

    def load_underlying(self, start_date, end_date) -> pd.DataFrame:
        days = pd.date_range(start=start_date, end=end_date, freq="B")
        frames: list[pd.DataFrame] = []
        for ts in days:
            path = self._candidate(self.cfg.underlying_dir, ts.date(), ("_underlying.csv", "_underlying.csv.gz"))
            if path is None:
                continue
            rows = read_rows(path)
            if not rows:
                continue
            df = pd.DataFrame(rows)
            df["timestamp"] = _to_timestamp(df["timestamp"], self.cfg.timezone)
            for col in ["open", "high", "low", "close", "volume"]:
                if col in df.columns:
                    df[col] = pd.to_numeric(df[col], errors="coerce")
            frames.append(df)
        if not frames:
            return pd.DataFrame()
        df = pd.concat(frames, ignore_index=True).sort_values("timestamp").set_index("timestamp")
        return df

    def load_quote_day(self, day) -> pd.DataFrame:
        path = self._candidate(self.cfg.options_dir, day, ("_options.csv", "_options.csv.gz", "_quote.csv", "_quote.csv.gz"))
        rows = read_rows(path) if path is not None else []
        if not rows:
            return pd.DataFrame()
        df = pd.DataFrame(rows)
        df["timestamp"] = _to_timestamp(df["timestamp"], self.cfg.timezone)
        df["strike"] = pd.to_numeric(df["strike"])
        df["bid"] = pd.to_numeric(df["bid"])
        df["ask"] = pd.to_numeric(df["ask"])
        if "delta" in df.columns:
            df["delta"] = pd.to_numeric(df["delta"], errors="coerce")
        if "open_interest" in df.columns:
            df["open_interest"] = pd.to_numeric(df["open_interest"], errors="coerce")
        df["right"] = df["right"].str.upper()
        return df.sort_values(["timestamp", "right", "strike"]).reset_index(drop=True)
