from pathlib import Path

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
from odte_lab.engine import run_backtest


def test_run_backtest_massive_simplified_smoke(tmp_path: Path) -> None:
    fixture_root = Path("0dte-lab/tests/fixtures/massive").resolve()
    cfg = QQQ0DTEConfig(
        backtest=BacktestConfig(start_date="2024-03-08", end_date="2024-03-08"),
        data=DataConfig(
            provider="massive_file",
            mode="simplified",
            underlying_dir=str(fixture_root / "underlying_1m"),
            options_dir=str(fixture_root / "options_1m"),
        ),
        signal=SignalConfig(
            kind="opening_momentum",
            trigger_pct=0.0015,
            entry_start="10:05",
            entry_end="10:15",
            step_minutes=1,
        ),
        selection=SelectionConfig(
            kind="exact_delta",
            target_delta=0.50,
            min_open_interest=0,
        ),
        execution=ExecutionConfig(
            mode="simplified",
            entry_price_mode="ask",
            exit_price_mode="bid",
            entry_slippage=0.0,
            exit_slippage=0.0,
            force_exit="11:30",
            take_profit_pct=0.25,
            stop_loss_pct=0.45,
            hard_stop_loss_pct=0.85,
            trail_activate_pct=0.0,
            trail_drawdown_pct=0.0,
        ),
        portfolio=PortfolioConfig(
            mode="fixed_fractional",
            initial_equity=10000.0,
            floor_equity=10000.0,
            fixed_fraction=0.15,
            contract_multiplier=100.0,
        ),
        outputs=OutputsConfig(output_dir=str(tmp_path / "out")),
    )
    result, coverage, output_dir = run_backtest(cfg)
    assert coverage["quality_tier"] == "massive_simplified"
    assert len(result.trades) == 1
    assert float(result.summary.iloc[0]["trade_count"]) == 1
    assert (output_dir / "base_trades.csv").exists()
