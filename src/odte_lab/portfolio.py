from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from odte_lab.domain import PortfolioConfig


@dataclass(frozen=True)
class ReplayResult:
    trades: pd.DataFrame
    summary: pd.DataFrame


def _next_tier(current: str, trade_ret: float) -> str:
    if current == "A":
        return "B" if trade_ret <= -0.25 else "A"
    if current == "B":
        if trade_ret > 0:
            return "A"
        if trade_ret <= -0.25:
            return "C"
        return "B"
    return "A" if trade_ret > 0 else "C"


def _ratio_for(direction: str | None, tier: str, cfg: PortfolioConfig) -> float:
    if cfg.mode == "fixed_fractional":
        ratio = cfg.fixed_fraction
    else:
        ratio = cfg.ratio_a if tier == "A" else cfg.ratio_b if tier == "B" else cfg.ratio_c
    if direction == "CALL":
        ratio *= cfg.call_size_mult
    return ratio


def _max_drawdown(values: list[float]) -> float:
    if not values:
        return 0.0
    s = pd.Series(values, dtype=float)
    peak = s.cummax()
    dd = (s - peak) / peak
    return float(dd.min())


def replay_single_leg_trades(base: pd.DataFrame, cfg: PortfolioConfig) -> ReplayResult:
    required = {"date", "direction", "trade_return", "contract_cost"}
    missing = required.difference(base.columns)
    if missing:
        raise ValueError(f"Missing required replay columns: {sorted(missing)}")

    df = base.copy()
    df["date"] = pd.to_datetime(df["date"]).dt.date
    df = df.sort_values("date").reset_index(drop=True)

    equity = cfg.initial_equity
    anchor = cfg.initial_equity
    tier = "A"
    topups_total = 0.0
    withdrawn_total = 0.0
    refill_count = 0
    consecutive_losses = 0

    rows: list[dict[str, object]] = []
    equity_curve: list[float] = []
    combined_curve: list[float] = []
    net_curve: list[float] = []

    for row in df.itertuples(index=False):
        base_row = row._asdict()
        if consecutive_losses >= 3 and equity < cfg.floor_equity:
            topup = cfg.floor_equity - equity
            equity += topup
            topups_total += topup
            refill_count += 1
            consecutive_losses = 0
            tier = "A"

        direction = str(row.direction).upper() if pd.notna(row.direction) else None
        trade_ret = float(row.trade_return)
        contract_cost = float(row.contract_cost)
        tier_before = tier
        ratio_used = _ratio_for(direction, tier, cfg)
        budget = equity * ratio_used
        contracts = int(budget // contract_cost) if contract_cost > 0 else 0
        filled_trade = contracts > 0
        skip_reason = ""
        pnl = 0.0
        notional_invested = 0.0

        if filled_trade:
            notional_invested = contracts * contract_cost
            pnl = notional_invested * trade_ret
            equity += pnl
            tier = _next_tier(tier, trade_ret) if cfg.mode == "dynamic_abc" else "A"
            consecutive_losses = consecutive_losses + 1 if trade_ret < 0 else 0
        else:
            skip_reason = "insufficient_contract_budget"

        while equity >= 2.0 * anchor:
            profit = equity - anchor
            withdrew = cfg.withdraw_ratio * profit
            equity -= withdrew
            withdrawn_total += withdrew
            anchor = equity

        combined_value = equity + withdrawn_total
        net_value = combined_value - topups_total
        equity_curve.append(equity)
        combined_curve.append(combined_value)
        net_curve.append(net_value)
        rows.append(
            {
                **base_row,
                "date": row.date,
                "direction": direction,
                "tier_used": tier_before,
                "tier_after": tier,
                "ratio_used": ratio_used,
                "budget": budget,
                "contract_cost": contract_cost,
                "contracts": contracts,
                "filled_trade": filled_trade,
                "trade_return": trade_ret,
                "notional_invested": notional_invested,
                "pnl": pnl,
                "skip_reason": skip_reason,
                "equity": equity,
                "withdrawn_total": withdrawn_total,
                "topups_total": topups_total,
                "combined_value": combined_value,
                "net_value_after_topups": net_value,
            }
        )

    trades = pd.DataFrame(rows)
    filled = trades[trades["filled_trade"] == True]
    days = max((pd.Timestamp(df["date"].max()) - pd.Timestamp(df["date"].min())).days, 1)
    net_value = float(trades["net_value_after_topups"].iloc[-1])
    combined_value = float(trades["combined_value"].iloc[-1])
    net_multiple = net_value / cfg.initial_equity
    net_cagr = net_multiple ** (365.0 / days) - 1.0
    summary = pd.DataFrame(
        [
            {
                "portfolio_mode": cfg.mode,
                "trade_count": int(len(filled)),
                "win_rate": float((filled["trade_return"] > 0).mean()) if len(filled) else 0.0,
                "avg_trade_return": float(filled["trade_return"].mean()) if len(filled) else 0.0,
                "avg_contracts": float(filled["contracts"].mean()) if len(filled) else 0.0,
                "refill_count": refill_count,
                "topups_total": topups_total,
                "combined_value": combined_value,
                "net_value_after_topups": net_value,
                "net_multiple": net_multiple,
                "net_cagr_pct": net_cagr * 100.0,
                "mdd_equity_only": _max_drawdown(equity_curve),
                "mdd_combined_value": _max_drawdown(combined_curve),
                "mdd_net_value": _max_drawdown(net_curve),
            }
        ]
    )
    return ReplayResult(trades=trades, summary=summary)
