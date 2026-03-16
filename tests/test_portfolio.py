import pandas as pd

from odte_lab.domain import PortfolioConfig
from odte_lab.portfolio import replay_single_leg_trades


def test_replay_single_leg_trades_dynamic_abc_runs() -> None:
    trades = pd.DataFrame(
        [
            {"date": "2024-03-08", "direction": "CALL", "trade_return": 0.25, "contract_cost": 134.0},
            {"date": "2024-03-11", "direction": "PUT", "trade_return": -0.45, "contract_cost": 154.0},
            {"date": "2024-03-12", "direction": "CALL", "trade_return": 0.30, "contract_cost": 140.0},
        ]
    )
    cfg = PortfolioConfig(
        mode="dynamic_abc",
        initial_equity=6000,
        floor_equity=6000,
        ratio_a=0.15,
        ratio_b=0.20,
        ratio_c=0.65,
        call_size_mult=0.85,
        withdraw_ratio=0.40,
        contract_multiplier=100.0,
    )
    result = replay_single_leg_trades(trades, cfg)
    assert len(result.trades) == 3
    assert float(result.summary.iloc[0]["trade_count"]) == 3
    assert "net_value_after_topups" in result.summary.columns
