from pathlib import Path

from odte_lab.config import load_config


def test_load_yaml_config_resolves_relative_paths() -> None:
    cfg = load_config(Path("0dte-lab/examples/qqq0dte/opening_momentum_base.yaml"))
    assert cfg.backtest.start_date == "2024-03-08"
    assert cfg.data.provider == "theta"
    assert cfg.outputs.output_dir.endswith("outputs/odte_lab/opening_momentum_base")
    assert cfg.data.quote_dir.endswith("data/theta/QQQ/0dte_quote_1m_093000_120000")
