from __future__ import annotations

import json
import tomllib
from pathlib import Path
from typing import Any

import yaml

from odte_lab.domain import (
    BacktestConfig,
    DataConfig,
    ExecutionConfig,
    OutputsConfig,
    PortfolioConfig,
    QQQ0DTEConfig,
    SelectionConfig,
    SignalConfig,
)


def _load_raw(path: Path) -> dict[str, Any]:
    suffix = path.suffix.lower()
    if suffix in {".yaml", ".yml"}:
        with path.open("r", encoding="utf-8") as fh:
            return yaml.safe_load(fh) or {}
    if suffix == ".json":
        return json.loads(path.read_text(encoding="utf-8"))
    if suffix == ".toml":
        return tomllib.loads(path.read_text(encoding="utf-8"))
    raise ValueError(f"Unsupported config extension: {path.suffix}")


def load_config(path: str | Path) -> QQQ0DTEConfig:
    cfg_path = Path(path).resolve()
    raw = _load_raw(cfg_path)
    cfg = QQQ0DTEConfig(
        backtest=BacktestConfig(**raw["backtest"]),
        data=DataConfig(**raw["data"]),
        signal=SignalConfig(**raw["signal"]),
        selection=SelectionConfig(**raw["selection"]),
        execution=ExecutionConfig(**raw["execution"]),
        portfolio=PortfolioConfig(**raw["portfolio"]),
        outputs=OutputsConfig(**raw["outputs"]),
    )
    return cfg.resolved(cfg_path.parent)
