from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path


@dataclass(frozen=True)
class DataConfig:
    provider: str
    mode: str
    timezone: str = "America/New_York"
    underlying_cache: str = ""
    underlying_dir: str = ""
    quote_dir: str = ""
    tradequote_dir: str = ""
    first_order_dir: str = ""
    open_interest_dir: str = ""
    options_dir: str = ""
    contracts_dir: str = ""

    def resolved(self, base_dir: Path) -> "DataConfig":
        def _resolve(value: str) -> str:
            if not value:
                return value
            path = Path(value)
            return str(path if path.is_absolute() else (base_dir / path).resolve())

        return DataConfig(
            provider=self.provider,
            mode=self.mode,
            timezone=self.timezone,
            underlying_cache=_resolve(self.underlying_cache),
            underlying_dir=_resolve(self.underlying_dir),
            quote_dir=_resolve(self.quote_dir),
            tradequote_dir=_resolve(self.tradequote_dir),
            first_order_dir=_resolve(self.first_order_dir),
            open_interest_dir=_resolve(self.open_interest_dir),
            options_dir=_resolve(self.options_dir),
            contracts_dir=_resolve(self.contracts_dir),
        )


@dataclass(frozen=True)
class SignalConfig:
    kind: str
    trigger_pct: float
    entry_start: str
    entry_end: str
    step_minutes: int = 1


@dataclass(frozen=True)
class BacktestConfig:
    start_date: str
    end_date: str


@dataclass(frozen=True)
class SelectionConfig:
    kind: str
    target_delta: float = 0.0
    delta_band: float = 0.0
    premium_target: float = 0.0
    min_open_interest: int = 0
    max_entry_spread_pct_mid: float = 0.0
    max_entry_spread_abs: float = 0.0


@dataclass(frozen=True)
class ExecutionConfig:
    mode: str
    entry_price_mode: str
    exit_price_mode: str
    entry_slippage: float
    exit_slippage: float
    force_exit: str
    take_profit_pct: float
    stop_loss_pct: float
    hard_stop_loss_pct: float
    trail_activate_pct: float
    trail_drawdown_pct: float


@dataclass(frozen=True)
class PortfolioConfig:
    mode: str
    initial_equity: float
    floor_equity: float
    fixed_fraction: float = 0.0
    ratio_a: float = 0.15
    ratio_b: float = 0.20
    ratio_c: float = 0.65
    call_size_mult: float = 0.85
    withdraw_ratio: float = 0.40
    contract_multiplier: float = 100.0


@dataclass(frozen=True)
class OutputsConfig:
    output_dir: str

    def resolved(self, base_dir: Path) -> "OutputsConfig":
        path = Path(self.output_dir)
        return OutputsConfig(output_dir=str(path if path.is_absolute() else (base_dir / path).resolve()))


@dataclass(frozen=True)
class QQQ0DTEConfig:
    backtest: BacktestConfig
    data: DataConfig
    signal: SignalConfig
    selection: SelectionConfig
    execution: ExecutionConfig
    portfolio: PortfolioConfig
    outputs: OutputsConfig

    def resolved(self, base_dir: Path) -> "QQQ0DTEConfig":
        return QQQ0DTEConfig(
            backtest=self.backtest,
            data=self.data.resolved(base_dir),
            signal=self.signal,
            selection=self.selection,
            execution=self.execution,
            portfolio=self.portfolio,
            outputs=self.outputs.resolved(base_dir),
        )

    def to_dict(self) -> dict:
        return asdict(self)
