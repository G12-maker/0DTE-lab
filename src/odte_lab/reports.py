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


def write_text(text: str, path: str | Path) -> Path:
    out = Path(path)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(text, encoding="utf-8")
    return out


def _first_summary_row(summary: pd.DataFrame) -> dict[str, object]:
    if summary.empty:
        return {}
    return {
        key: value.item() if hasattr(value, "item") else value
        for key, value in summary.iloc[0].to_dict().items()
    }


def build_quick_summary(summary: pd.DataFrame, coverage_tier: str) -> dict[str, object]:
    row = _first_summary_row(summary)
    trade_count = int(row.get("trade_count", 0) or 0)
    win_rate = float(row.get("win_rate", 0.0) or 0.0) * 100.0
    avg_trade_return = float(row.get("avg_trade_return", 0.0) or 0.0) * 100.0
    net_value = float(row.get("net_value_after_topups", 0.0) or 0.0)
    net_multiple = float(row.get("net_multiple", 0.0) or 0.0)
    net_cagr_pct = float(row.get("net_cagr_pct", 0.0) or 0.0)
    refill_count = int(row.get("refill_count", 0) or 0)
    topups_total = float(row.get("topups_total", 0.0) or 0.0)
    days_seen = int(row.get("days_seen", 0) or 0)
    portfolio_mode = str(row.get("portfolio_mode", "unknown"))
    cagr_meaningful = days_seen >= 90 and trade_count >= 20
    return {
        "quality_tier": coverage_tier,
        "portfolio_mode": portfolio_mode,
        "trade_count": trade_count,
        "days_seen": days_seen,
        "win_rate_pct": round(win_rate, 2),
        "avg_trade_return_pct": round(avg_trade_return, 2),
        "final_net_value": round(net_value, 2),
        "net_multiple": round(net_multiple, 4),
        "net_cagr_pct": round(net_cagr_pct, 2) if cagr_meaningful else None,
        "cagr_meaningful": cagr_meaningful,
        "refill_count": refill_count,
        "topups_total": round(topups_total, 2),
    }


def write_quick_summary(summary: pd.DataFrame, coverage_tier: str, output_dir: Path) -> None:
    quick = build_quick_summary(summary, coverage_tier)
    lines = [
        f"quality_tier: {quick['quality_tier']}",
        f"portfolio_mode: {quick['portfolio_mode']}",
        f"trade_count: {quick['trade_count']}",
        f"days_seen: {quick['days_seen']}",
        f"win_rate_pct: {quick['win_rate_pct']}",
        f"avg_trade_return_pct: {quick['avg_trade_return_pct']}",
        f"final_net_value: {quick['final_net_value']}",
        f"net_multiple: {quick['net_multiple']}",
        f"refill_count: {quick['refill_count']}",
        f"topups_total: {quick['topups_total']}",
    ]
    if quick["cagr_meaningful"]:
        lines.append(f"net_cagr_pct: {quick['net_cagr_pct']}")
    else:
        lines.append("net_cagr_pct: not shown for very short samples")
    write_json(quick, output_dir / "quick_summary.json")
    write_text("\n".join(lines) + "\n", output_dir / "quick_summary.txt")


def print_run_summary(output_dir: Path, trades_count: int, summary_rows: int, coverage_tier: str, summary: pd.DataFrame | None = None) -> None:
    print(f"output_dir={output_dir}")
    print(f"trades={trades_count}")
    print(f"summary_rows={summary_rows}")
    print(f"coverage_tier={coverage_tier}")
    if summary is not None and not summary.empty:
        quick = build_quick_summary(summary, coverage_tier)
        print(f"final_net_value={quick['final_net_value']}")
        print(f"win_rate_pct={quick['win_rate_pct']}")
        print(f"net_multiple={quick['net_multiple']}")
        if quick["cagr_meaningful"]:
            print(f"net_cagr_pct={quick['net_cagr_pct']}")
