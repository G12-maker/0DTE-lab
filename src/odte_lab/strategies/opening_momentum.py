from __future__ import annotations

from dataclasses import dataclass

from odte_lab.domain import SelectionConfig, SignalConfig


@dataclass(frozen=True)
class OpeningMomentumTemplate:
    signal: SignalConfig
    selection: SelectionConfig

    def summary(self) -> dict[str, object]:
        return {
            "kind": "opening_momentum",
            "trigger_pct": self.signal.trigger_pct,
            "entry_window": [self.signal.entry_start, self.signal.entry_end],
            "selection_kind": self.selection.kind,
            "target_delta": self.selection.target_delta,
        }


@dataclass(frozen=True)
class OpeningReversalTemplate:
    signal: SignalConfig
    selection: SelectionConfig

    def summary(self) -> dict[str, object]:
        return {
            "kind": "opening_reversal",
            "trigger_pct": self.signal.trigger_pct,
            "entry_window": [self.signal.entry_start, self.signal.entry_end],
            "selection_kind": self.selection.kind,
            "target_delta": self.selection.target_delta,
        }


@dataclass(frozen=True)
class DelayedRescanConfirmationTemplate:
    signal: SignalConfig
    selection: SelectionConfig

    def summary(self) -> dict[str, object]:
        return {
            "kind": "delayed_rescan_confirmation",
            "trigger_pct": self.signal.trigger_pct,
            "entry_window": [self.signal.entry_start, self.signal.entry_end],
            "selection_kind": self.selection.kind,
            "target_delta": self.selection.target_delta,
        }
