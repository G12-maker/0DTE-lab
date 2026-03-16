from __future__ import annotations

import json
from pathlib import Path

import pandas as pd


def ensure_output_dir(path: str | Path) -> Path:
    output_dir = Path(path)
    output_dir.mkdir(parents=True, exist_ok=True)
    return output_dir


def write_csv(df: pd.DataFrame, path: str | Path) -> Path:
    out = Path(path)
    out.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(out, index=False)
    return out


def write_json(payload: dict, path: str | Path) -> Path:
    out = Path(path)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    return out


def print_run_summary(output_dir: Path, trades_count: int, summary_rows: int, coverage_tier: str) -> None:
    print(f"output_dir={output_dir}")
    print(f"trades={trades_count}")
    print(f"summary_rows={summary_rows}")
    print(f"coverage_tier={coverage_tier}")
