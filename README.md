# 0DTE-lab

`0DTE-lab` is a research tool for testing `QQQ 0DTE` option ideas.

It is built for traders who want a repeatable backtest workflow, with a simple no-Theta demo path and a higher-fidelity Theta research path. The first goal is simple: copy a command, run a demo, and understand where the result files are.

## Why This Project

- Focused on `QQQ 0DTE` instead of general options tooling
- Supports both a simple demo mode and a higher-fidelity Theta mode
- Produces standardized result files for repeatable research

## Best First Command

If you only try one thing, start here:

```bash
cd 0dte-lab
PYTHONPATH=src python -m odte_lab qqq0dte backtest \
  --config examples/qqq0dte/demo_no_theta.yaml \
  --output-dir /tmp/odte-lab-demo
```

## What You Can Do With It

- Backtest `QQQ 0DTE` single-leg ideas
- Compare a higher-fidelity Theta workflow with a simpler onboarding workflow
- Re-run the same config and get standardized result files
- Study entries, exits, and portfolio rules without building your own framework first

## What It Is Not

- Not a broker integration
- Not an auto-trading bot
- Not a guarantee that backtest fills match live fills
- Not a multi-leg options platform

## Current Maturity

`0dte-lab` should currently be treated as an **alpha research tool**.

Important boundaries:

- `theta_realistic` is the higher-fidelity mode and should be treated as the main research mode
- `massive_simplified` is for onboarding, smoke tests, and low-friction experimentation
- Results from `massive_simplified` should **not** be compared directly with `theta_realistic`
- The framework is already useful, but some strategy migrations from older private research code are still being aligned

## Start Here

Choose the path that matches you.

### I do not have Theta

Start with the bundled Massive sample. This is the easiest way to confirm the project works.

If you only try one thing, start with this command:

```bash
cd 0dte-lab
PYTHONPATH=src python -m odte_lab qqq0dte backtest \
  --config examples/qqq0dte/demo_no_theta.yaml \
  --output-dir /tmp/odte-lab-demo
```

What you should see:

- a command summary in the terminal
- a result folder at `/tmp/odte-lab-demo`
- files such as `summary.csv` and `trades.csv`

### I have Theta data already

First run a dry-run so the tool checks your local paths and writes metadata without running a full backtest.

```bash
cd 0dte-lab
PYTHONPATH=src python -m odte_lab qqq0dte backtest \
  --config examples/qqq0dte/theta_smoke.yaml \
  --dry-run \
  --output-dir /tmp/odte-lab-theta-dryrun
```

If that looks good, run a real backtest:

```bash
cd 0dte-lab
PYTHONPATH=src python -m odte_lab qqq0dte backtest \
  --config examples/qqq0dte/theta_smoke.yaml \
  --output-dir /tmp/odte-lab-theta-run
```

## 3-Minute Setup

### Option 1: Run without installing

```bash
cd 0dte-lab
PYTHONPATH=src python -m odte_lab --help
```

### Option 2: Editable install

```bash
cd 0dte-lab
python -m venv .venv
.venv/bin/pip install -e .
odte-lab qqq0dte --help
```

## Which Example Should I Use?

Use the files in `examples/qqq0dte/`.

- `demo_no_theta.yaml`
  - easiest first run
  - uses bundled sample data
  - no Theta subscription needed
- `theta_smoke.yaml`
  - short Theta example
  - best first step if you already have local Theta data
- `opening_momentum_base.yaml`
  - fuller Theta configuration
  - useful as a base template for your own research

There is also a short guide at `examples/qqq0dte/README.md`.

## Common Use Cases

### 1. I just want to see one working example

```bash
cd 0dte-lab
PYTHONPATH=src python -m odte_lab qqq0dte backtest \
  --config examples/qqq0dte/demo_no_theta.yaml
```

### 2. I want to check whether my Theta paths are valid

```bash
cd 0dte-lab
PYTHONPATH=src python -m odte_lab qqq0dte backtest \
  --config examples/qqq0dte/theta_smoke.yaml \
  --dry-run
```

### 3. I want to replay an existing trade file through portfolio rules

```bash
cd 0dte-lab
PYTHONPATH=src python -m odte_lab qqq0dte replay \
  --trades /path/to/trades.csv \
  --config examples/qqq0dte/opening_momentum_base.yaml \
  --output-dir /tmp/odte-lab-replay
```

## How To Read The Results

Every run writes a small set of standard files.

- `quick_summary.txt`
  - the easiest human-readable summary
  - start here if you want the simplest result view
- `quick_summary.json`
  - the same quick summary in machine-readable form
- `summary.csv`
  - the high-level result table
  - use this when you want the full metric table
- `trades.csv`
  - trade-by-trade results after portfolio sizing
  - use this when you want to inspect wins, losses, and exits
- `base_trades.csv`
  - pre-portfolio trade construction details
  - useful when comparing strategy logic or contract selection
- `coverage.json`
  - tells you what data mode you actually used
  - especially important for checking `theta_realistic` vs `massive_simplified`
- `run_config.json`
  - the exact config used for the run
  - use this when you want reproducibility

## Data Modes

`0dte-lab` supports 2 data modes.

### `theta`

Use this when you want the higher-fidelity research path.

Current Theta path can use:

- underlying minute cache
- option minute quotes
- optional `first_order`
- optional `open_interest`
- `trade_quote` replay for more realistic exits

Output quality tier:

- `theta_realistic`

### `massive_file`

Use this when you want the easiest onboarding path.

Current Massive path can use:

- local daily underlying minute files
- local daily option minute files
- simplified minute-based entry and exit logic

Output quality tier:

- `massive_simplified`

## The Most Important Warning

Do not mix these two ideas:

- `massive_simplified` is useful for learning the tool and testing configs
- `theta_realistic` is the mode to use for more serious research

If two runs use different quality tiers, do not treat their PnL numbers as directly comparable.

## What The Tool Supports Today

- `QQQ 0DTE`
- single-leg strategies
- CLI entrypoint: `odte-lab`
- config loading from YAML / JSON / TOML
- strategy templates:
  - `opening_momentum`
  - `opening_reversal`
  - `delayed_rescan_confirmation`
- selection methods:
  - `exact_delta`
  - `premium_target`
  - nearest moneyness fallback
- portfolio modes:
  - `fixed_fractional`
  - `dynamic_abc`
- integer contracts
- top-ups
- withdrawals

## What Is Not Implemented Yet

- multi-leg structures
- broker routing
- direct Massive API downloader
- walk-forward CLI
- built-in charts or dashboard

## Project Layout

```text
0dte-lab/
  examples/
    qqq0dte/
  sample_data/
    massive/
  src/odte_lab/
  tests/
```

Useful files:

- `pyproject.toml`
- `src/odte_lab/cli.py`
- `src/odte_lab/engine.py`
- `src/odte_lab/providers/theta.py`
- `src/odte_lab/providers/massive.py`

## Quick Terminal Snapshot

Example output from the Massive demo:

```text
output_dir=/tmp/odte-lab-demo
trades=1
summary_rows=1
coverage_tier=massive_simplified
```

## FAQ

### Do I need to be a programmer?

No, but you do need to be comfortable copying commands into a terminal.

### I do not have Theta. Can I still use this?

Yes. Start with `demo_no_theta.yaml`.

### Which mode should I trust more?

`theta_realistic` is the higher-fidelity research mode.
`massive_simplified` is mainly for onboarding and smoke tests.

### Which file should I read first after a run?

Open `summary.csv` first.

### Why does my result not match someone else's screenshot?

Check `coverage.json` first. The most common reason is that one run used `theta_realistic` and the other used `massive_simplified`.

### Is this safe to use for live money decisions by itself?

No. Treat it as a research tool, not as an execution guarantee.

## Testing

Run the project tests from the repo root:

```bash
PYTHONPATH=src python -m pytest tests -q
```

## Known Limitations

- The project is still alpha
- `massive_simplified` is intentionally simpler than the Theta path
- Some strategy migrations from older internal research are still being aligned
- No broker integration is included
- No built-in chart UI exists yet

## Disclaimer

This repository is for research and educational use only.

Options trading is risky. Backtest results can be misleading. Simplified fills, missing data, slippage differences, and regime changes can all cause real-world performance to differ materially from historical simulations.

You are responsible for validating any strategy before using real capital.
