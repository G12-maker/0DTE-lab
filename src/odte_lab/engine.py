from __future__ import annotations

from datetime import date, datetime, time, timedelta
from pathlib import Path

import pandas as pd

from odte_lab.domain import ExecutionConfig, QQQ0DTEConfig, SelectionConfig, SignalConfig
from odte_lab.portfolio import ReplayResult, replay_single_leg_trades
from odte_lab.pricing import bs_delta, implied_vol
from odte_lab.providers import ProviderFactory
from odte_lab.reports import ensure_output_dir, write_csv, write_json, write_quick_summary


def inspect_provider(cfg: QQQ0DTEConfig) -> dict:
    provider = ProviderFactory.build(cfg.data)
    return provider.inspect().to_dict()


def _parse_time_token(value: str) -> time:
    return time.fromisoformat(value)


def _tau_years(entry_ts: pd.Timestamp) -> float:
    close_ts = entry_ts.normalize() + pd.Timedelta(hours=16)
    seconds = max((close_ts - entry_ts).total_seconds(), 60.0)
    return seconds / (365.0 * 24.0 * 60.0 * 60.0)


def _find_signal(day_df: pd.DataFrame, cfg: SignalConfig) -> tuple[pd.Timestamp | None, str | None, float | None]:
    if day_df.empty:
        return None, None, None
    start_time = _parse_time_token(cfg.entry_start)
    end_time = _parse_time_token(cfg.entry_end)
    if start_time not in set(day_df.index.time):
        return None, None, None
    open_price = float(day_df[day_df.index.time == time(9, 30)].iloc[0]["open"])
    cur = datetime.combine(date(2000, 1, 1), start_time)
    end_dt = datetime.combine(date(2000, 1, 1), end_time)
    candidate_times: list[time] = []
    while cur <= end_dt:
        candidate_times.append(cur.time())
        cur += timedelta(minutes=cfg.step_minutes)

    window = day_df[[ts in set(candidate_times) for ts in day_df.index.time]]
    for ts, row in window.sort_index().iterrows():
        move = (float(row["close"]) - open_price) / open_price
        if cfg.kind == "opening_momentum":
            if move >= cfg.trigger_pct:
                return ts, "CALL", float(row["close"])
            if move <= -cfg.trigger_pct:
                return ts, "PUT", float(row["close"])
        elif cfg.kind == "opening_reversal":
            if move >= cfg.trigger_pct:
                return ts, "PUT", float(row["close"])
            if move <= -cfg.trigger_pct:
                return ts, "CALL", float(row["close"])
        elif cfg.kind == "delayed_rescan_confirmation":
            if move >= cfg.trigger_pct:
                next_ts = ts + pd.Timedelta(minutes=cfg.step_minutes)
                if next_ts in day_df.index and (float(day_df.loc[next_ts, "close"]) - open_price) / open_price >= cfg.trigger_pct:
                    return next_ts, "CALL", float(day_df.loc[next_ts, "close"])
            if move <= -cfg.trigger_pct:
                next_ts = ts + pd.Timedelta(minutes=cfg.step_minutes)
                if next_ts in day_df.index and (float(day_df.loc[next_ts, "close"]) - open_price) / open_price <= -cfg.trigger_pct:
                    return next_ts, "PUT", float(day_df.loc[next_ts, "close"])
    return None, None, None


def _apply_liquidity_filters(df: pd.DataFrame, selection: SelectionConfig) -> pd.DataFrame:
    out = df.copy()
    if "open_interest" not in out.columns:
        out["open_interest"] = pd.NA
    if selection.min_open_interest > 0:
        out = out[out["open_interest"].fillna(-1) >= selection.min_open_interest].copy()
    if selection.max_entry_spread_abs > 0 or selection.max_entry_spread_pct_mid > 0:
        out["entry_spread_abs"] = out["ask"] - out["bid"]
        out["mid"] = (out["ask"] + out["bid"]) / 2.0
        out["entry_spread_pct_mid"] = out["entry_spread_abs"] / out["mid"].replace(0, pd.NA)
        if selection.max_entry_spread_abs > 0:
            out = out[out["entry_spread_abs"].fillna(999.0) <= selection.max_entry_spread_abs].copy()
        if selection.max_entry_spread_pct_mid > 0:
            out = out[out["entry_spread_pct_mid"].fillna(999.0) <= selection.max_entry_spread_pct_mid].copy()
    return out


def _select_contract(
    quote_df: pd.DataFrame,
    entry_ts: pd.Timestamp,
    right: str,
    underlying_px: float,
    selection: SelectionConfig,
    first_order_df: pd.DataFrame | None,
    open_interest_df: pd.DataFrame | None,
) -> tuple[pd.Series | None, str]:
    candidates = quote_df[
        (quote_df["timestamp"] == entry_ts)
        & (quote_df["right"] == right)
        & (quote_df["ask"] > 0)
    ].copy()
    if candidates.empty:
        return None, "none"
    if open_interest_df is not None and not open_interest_df.empty:
        candidates = candidates.merge(open_interest_df[["right", "strike", "open_interest"]], on=["right", "strike"], how="left")
    candidates = _apply_liquidity_filters(candidates, selection)
    if candidates.empty:
        return None, "none"

    used_first_order = False
    if first_order_df is not None and not first_order_df.empty and selection.kind == "exact_delta" and selection.target_delta > 0:
        greeks = first_order_df[
            (first_order_df["timestamp"] == entry_ts)
            & (first_order_df["right"] == right)
            & (first_order_df["strike"].isin(candidates["strike"]))
        ][["right", "strike", "delta"]].copy()
        if not greeks.empty:
            candidates = candidates.merge(greeks, on=["right", "strike"], how="left")
            used_first_order = True

    if selection.kind == "exact_delta" and selection.target_delta > 0:
        if "delta" not in candidates.columns or candidates["delta"].isna().all():
            tau = _tau_years(entry_ts)
            mids = (candidates["ask"] + candidates["bid"]) / 2.0
            ivs = [
                implied_vol(float(mid), underlying_px, float(strike), tau, right)
                for mid, strike in zip(mids, candidates["strike"])
            ]
            candidates["delta"] = [
                bs_delta(underlying_px, float(strike), tau, iv, right) if iv is not None else pd.NA
                for iv, strike in zip(ivs, candidates["strike"])
            ]
        candidates = candidates[candidates["delta"].notna()].copy()
        if candidates.empty:
            return None, "none"
        target_signed = selection.target_delta if right == "CALL" else -selection.target_delta
        candidates["delta_gap"] = (candidates["delta"] - target_signed).abs()
        candidates["abs_moneyness"] = (candidates["strike"] - underlying_px).abs()
        candidates["spread"] = candidates["ask"] - candidates["bid"]
        if "mid" not in candidates.columns:
            candidates["mid"] = (candidates["ask"] + candidates["bid"]) / 2.0
        candidates["spread_pct_mid"] = candidates["spread"] / candidates["mid"].replace(0, pd.NA)
        selected = candidates.sort_values(
            ["delta_gap", "spread_pct_mid", "abs_moneyness", "ask"],
            ascending=[True, True, True, True],
            na_position="last",
        ).iloc[0]
        return selected, "first_order" if used_first_order else "quote_iv_estimate"

    if selection.kind == "premium_target" and selection.premium_target > 0:
        candidates["premium_gap"] = (candidates["ask"] - selection.premium_target).abs()
        return candidates.sort_values(["premium_gap", "ask"], ascending=[True, True]).iloc[0], "premium_target"

    candidates["abs_moneyness"] = (candidates["strike"] - underlying_px).abs()
    return candidates.sort_values(["abs_moneyness", "ask"], ascending=[True, True]).iloc[0], "moneyness_fallback"


def _simulate_minute_exit(contract_quotes: pd.DataFrame, entry_ts: pd.Timestamp, execution: ExecutionConfig) -> tuple[float, str, pd.Timestamp]:
    entry_row = contract_quotes[contract_quotes["timestamp"] == entry_ts]
    if entry_row.empty:
        raise RuntimeError("Missing entry quote")
    entry_ask = float(entry_row.iloc[0]["ask"]) + execution.entry_slippage
    if entry_ask <= 0:
        raise RuntimeError("Non-positive entry ask")

    post = contract_quotes[contract_quotes["timestamp"] >= entry_ts].sort_values("timestamp")
    force_exit = _parse_time_token(execution.force_exit)
    trail_armed = False
    peak_exec_ret = float("-inf")

    for _, row in post.iterrows():
        ts = row["timestamp"]
        bid = max(float(row["bid"]) - execution.exit_slippage, 0.0)
        ask = float(row["ask"])
        if ask <= 0 and bid <= 0:
            continue
        exec_ret = (bid / entry_ask) - 1.0
        if exec_ret <= -execution.hard_stop_loss_pct:
            return exec_ret, "hard_sl", ts
        if ts.time() >= time(10, 25) and exec_ret <= -execution.stop_loss_pct:
            return exec_ret, "sl", ts
        if execution.trail_activate_pct > 0:
            if not trail_armed and exec_ret >= execution.trail_activate_pct:
                trail_armed = True
                peak_exec_ret = exec_ret
            elif trail_armed:
                peak_exec_ret = max(peak_exec_ret, exec_ret)
                if exec_ret <= peak_exec_ret - execution.trail_drawdown_pct:
                    return exec_ret, "trail_tp", ts
        elif execution.take_profit_pct > 0 and exec_ret >= execution.take_profit_pct:
            return exec_ret, "tp", ts
        if ts.time() >= force_exit:
            return exec_ret, "force_exit", ts
    raise RuntimeError("No exit quote found")


def _simulate_tradequote_exit(
    tradequotes: pd.DataFrame | None,
    contract_quotes: pd.DataFrame,
    entry_ts: pd.Timestamp,
    execution: ExecutionConfig,
) -> tuple[float, str, pd.Timestamp]:
    if tradequotes is None or tradequotes.empty:
        return _simulate_minute_exit(contract_quotes, entry_ts, execution)
    entry_row = contract_quotes[contract_quotes["timestamp"] == entry_ts]
    if entry_row.empty:
        raise RuntimeError("Missing entry quote")
    entry_ask = float(entry_row.iloc[0]["ask"]) + execution.entry_slippage
    force_exit = _parse_time_token(execution.force_exit)
    post = tradequotes[tradequotes["quote_timestamp"] >= entry_ts].sort_values(["quote_timestamp", "trade_timestamp"])
    trail_armed = False
    peak_exec_ret = float("-inf")
    for row in post.itertuples(index=False):
        ts = row.quote_timestamp
        bid = max(float(row.bid) - execution.exit_slippage, 0.0)
        ask = float(row.ask)
        if ask <= 0 and bid <= 0:
            continue
        exec_ret = (bid / entry_ask) - 1.0
        if exec_ret <= -execution.hard_stop_loss_pct:
            return exec_ret, "hard_sl", ts
        if ts.time() >= time(10, 25) and exec_ret <= -execution.stop_loss_pct:
            return exec_ret, "sl", ts
        if execution.trail_activate_pct > 0:
            if not trail_armed and exec_ret >= execution.trail_activate_pct:
                trail_armed = True
                peak_exec_ret = exec_ret
            elif trail_armed:
                peak_exec_ret = max(peak_exec_ret, exec_ret)
                if exec_ret <= peak_exec_ret - execution.trail_drawdown_pct:
                    return exec_ret, "trail_tp", ts
        elif execution.take_profit_pct > 0 and exec_ret >= execution.take_profit_pct:
            return exec_ret, "tp", ts
        if ts.time() >= force_exit:
            return exec_ret, "force_exit", ts
    return _simulate_minute_exit(contract_quotes, entry_ts, execution)


def _build_base_trades(cfg: QQQ0DTEConfig) -> tuple[pd.DataFrame, dict]:
    provider = ProviderFactory.build(cfg.data)
    start_date = date.fromisoformat(cfg.backtest.start_date)
    end_date = date.fromisoformat(cfg.backtest.end_date)
    underlying_df = provider.load_underlying(start_date, end_date)
    if underlying_df.empty:
        raise RuntimeError("No underlying data found for configured range")

    rows: list[dict[str, object]] = []
    stats = {
        "days_seen": 0,
        "signals_found": 0,
        "contracts_selected": 0,
        "trades_built": 0,
        "skipped_no_quote": 0,
        "skipped_no_contract": 0,
        "selection_source_first_order": 0,
        "selection_source_quote_iv_estimate": 0,
        "selection_source_premium_target": 0,
        "selection_source_moneyness_fallback": 0,
    }

    for current_day in sorted({x.date() for x in underlying_df.index}):
        day_df = underlying_df[underlying_df.index.date == current_day]
        if day_df.empty:
            continue
        stats["days_seen"] += 1
        signal_ts, direction, underlying_px = _find_signal(day_df, cfg.signal)
        if signal_ts is None or direction is None or underlying_px is None:
            continue
        stats["signals_found"] += 1
        quotes = provider.load_quote_day(current_day)
        if quotes.empty:
            stats["skipped_no_quote"] += 1
            continue
        first_order = provider.load_first_order_day(current_day)
        open_interest = provider.load_open_interest_day(current_day)
        contract, selection_source = _select_contract(
            quote_df=quotes,
            entry_ts=signal_ts,
            right=direction,
            underlying_px=underlying_px,
            selection=cfg.selection,
            first_order_df=first_order,
            open_interest_df=open_interest,
        )
        if contract is None:
            stats["skipped_no_contract"] += 1
            continue
        stats["contracts_selected"] += 1
        stats[f"selection_source_{selection_source}"] += 1
        strike = float(contract["strike"])
        contract_quotes = quotes[(quotes["right"] == direction) & (quotes["strike"] == strike)].copy()
        if contract_quotes.empty:
            stats["skipped_no_quote"] += 1
            continue
        if cfg.execution.mode == "realistic" and cfg.data.provider == "theta":
            tradequotes = provider.load_tradequote_day(current_day, direction, strike)
            trade_ret, reason, exit_ts = _simulate_tradequote_exit(tradequotes, contract_quotes, signal_ts, cfg.execution)
        else:
            trade_ret, reason, exit_ts = _simulate_minute_exit(contract_quotes, signal_ts, cfg.execution)
        entry_row = contract_quotes[contract_quotes["timestamp"] == signal_ts].iloc[0]
        entry_bid = float(entry_row["bid"])
        raw_entry_ask = float(entry_row["ask"])
        entry_ask = raw_entry_ask + cfg.execution.entry_slippage
        entry_mid = (raw_entry_ask + entry_bid) / 2.0 if (raw_entry_ask > 0 or entry_bid > 0) else 0.0
        entry_spread_abs = raw_entry_ask - entry_bid
        entry_spread_pct_mid = entry_spread_abs / entry_mid if entry_mid > 0 else pd.NA
        rows.append(
            {
                "date": current_day,
                "signal_time": signal_ts,
                "entry_time": signal_ts,
                "exit_time": exit_ts,
                "direction": direction,
                "strike": strike,
                "contract_cost": entry_ask * cfg.portfolio.contract_multiplier,
                "trade_return": trade_ret,
                "reason": reason,
                "selected_delta": float(contract["delta"]) if "delta" in contract and pd.notna(contract["delta"]) else pd.NA,
                "selected_open_interest": (
                    float(contract["open_interest"])
                    if "open_interest" in contract and pd.notna(contract["open_interest"])
                    else pd.NA
                ),
                "selection_source": selection_source,
                "entry_spread_pct_mid": entry_spread_pct_mid,
                "quality_tier": "theta_realistic" if cfg.execution.mode == "realistic" and cfg.data.provider == "theta" else "simplified_minute",
            }
        )
        stats["trades_built"] += 1
    return pd.DataFrame(rows), stats


def run_backtest(cfg: QQQ0DTEConfig) -> tuple[ReplayResult, dict, Path]:
    base_trades, stats = _build_base_trades(cfg)
    coverage = inspect_provider(cfg)
    if base_trades.empty:
        replay = ReplayResult(trades=pd.DataFrame(), summary=pd.DataFrame([{"trade_count": 0, **stats}]))
    else:
        replay = replay_single_leg_trades(base_trades, cfg.portfolio)
        for key, value in stats.items():
            replay.summary[key] = value
    output_dir = ensure_output_dir(cfg.outputs.output_dir)
    write_csv(base_trades, output_dir / "base_trades.csv")
    write_csv(replay.trades, output_dir / "trades.csv")
    write_csv(replay.summary, output_dir / "summary.csv")
    write_json(cfg.to_dict(), output_dir / "run_config.json")
    write_json(coverage, output_dir / "coverage.json")
    write_quick_summary(replay.summary, coverage["quality_tier"], output_dir)
    return replay, coverage, output_dir


def replay_trades(trades_path: str | Path, cfg: QQQ0DTEConfig) -> tuple[ReplayResult, dict, Path]:
    base = pd.read_csv(trades_path)
    result = replay_single_leg_trades(base, cfg.portfolio)
    coverage = inspect_provider(cfg)
    output_dir = ensure_output_dir(cfg.outputs.output_dir)
    write_csv(result.trades, output_dir / "trades.csv")
    write_csv(result.summary, output_dir / "summary.csv")
    write_json(cfg.to_dict(), output_dir / "run_config.json")
    write_json(coverage, output_dir / "coverage.json")
    write_quick_summary(result.summary, coverage["quality_tier"], output_dir)
    return result, coverage, output_dir
