from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

from odte_lab.config import load_config
from odte_lab.engine import inspect_provider, replay_trades, run_backtest
from odte_lab.reports import ensure_output_dir, print_run_summary, write_csv, write_json, write_quick_summary


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="odte-lab")
    subparsers = parser.add_subparsers(dest="command", required=True)

    qqq_parser = subparsers.add_parser("qqq0dte", help="QQQ 0DTE commands.")
    qqq_subparsers = qqq_parser.add_subparsers(dest="qqq_command", required=True)

    replay_parser = qqq_subparsers.add_parser("replay", help="Replay a standardized single-leg trade file.")
    replay_parser.add_argument("--trades", required=True)
    replay_parser.add_argument("--config", required=True)
    replay_parser.add_argument("--output-dir", default="")
    replay_parser.set_defaults(handler=handle_replay)

    backtest_parser = qqq_subparsers.add_parser("backtest", help="Validate config and inspect provider coverage.")
    backtest_parser.add_argument("--config", required=True)
    backtest_parser.add_argument("--dry-run", action="store_true")
    backtest_parser.add_argument("--output-dir", default="")
    backtest_parser.set_defaults(handler=handle_backtest)

    return parser


def handle_replay(args: argparse.Namespace) -> int:
    cfg = load_config(args.config)
    if args.output_dir:
        cfg = cfg.__class__(
            backtest=cfg.backtest,
            data=cfg.data,
            signal=cfg.signal,
            selection=cfg.selection,
            execution=cfg.execution,
            portfolio=cfg.portfolio,
            outputs=cfg.outputs.__class__(output_dir=str(Path(args.output_dir).resolve())),
        )
    result, coverage, output_dir = replay_trades(args.trades, cfg)
    print_run_summary(
        output_dir=output_dir,
        trades_count=len(result.trades),
        summary_rows=len(result.summary),
        coverage_tier=coverage["quality_tier"],
        summary=result.summary,
    )
    return 0


def handle_backtest(args: argparse.Namespace) -> int:
    cfg = load_config(args.config)
    if args.output_dir:
        cfg = cfg.__class__(
            backtest=cfg.backtest,
            data=cfg.data,
            signal=cfg.signal,
            selection=cfg.selection,
            execution=cfg.execution,
            portfolio=cfg.portfolio,
            outputs=cfg.outputs.__class__(output_dir=str(Path(args.output_dir).resolve())),
        )
    output_dir = ensure_output_dir(cfg.outputs.output_dir)
    coverage = inspect_provider(cfg)
    if not args.dry_run:
        result, coverage, output_dir = run_backtest(cfg)
        print_run_summary(
            output_dir=output_dir,
            trades_count=len(result.trades),
            summary_rows=len(result.summary),
            coverage_tier=coverage["quality_tier"],
            summary=result.summary,
        )
        return 0
    write_json(cfg.to_dict(), output_dir / "run_config.json")
    write_json(coverage, output_dir / "coverage.json")
    write_csv(pd.DataFrame(), output_dir / "trades.csv")
    write_csv(pd.DataFrame([{"status": "dry_run"}]), output_dir / "summary.csv")
    write_quick_summary(pd.DataFrame([{"portfolio_mode": cfg.portfolio.mode, "trade_count": 0}]), coverage["quality_tier"], output_dir)
    print_run_summary(output_dir=output_dir, trades_count=0, summary_rows=1, coverage_tier=coverage["quality_tier"])
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.handler(args)
