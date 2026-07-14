"""Aggregatable, low-cardinality M31.5 eligibility shadow telemetry.

The application already uses structured process logging as its operational
telemetry mechanism.  This module adds process-local counters that can be
snapshotted by operations/tests and supplies low-cardinality labels for the
structured log sink.  It intentionally has no ORM dependency or database
table: eligibility observation must not create persistence side effects.
"""
from __future__ import annotations

import threading
from collections import Counter
from dataclasses import asdict, dataclass
from typing import Dict, Tuple

__all__ = [
    "EligibilityObservation",
    "EligibilityMetricKey",
    "EligibilityMetricUpdate",
    "record_execution_eligibility_observation",
    "execution_eligibility_counter_snapshot",
    "reset_execution_eligibility_observability",
]


@dataclass(frozen=True)
class EligibilityObservation:
    boundary: str
    eligibility_outcome: str
    resolution_status: str
    instrument_form: str
    execution_role: str
    cutover_mode: str
    registry_failure: bool
    classification_agreement: str


@dataclass(frozen=True)
class EligibilityMetricKey:
    """The complete metric label set; deliberately contains no identity."""

    boundary: str
    eligibility_outcome: str
    resolution_status: str
    instrument_form: str
    execution_role: str
    cutover_mode: str
    registry_failure: bool
    classification_agreement: str


@dataclass(frozen=True)
class EligibilityMetricUpdate:
    labels: EligibilityMetricKey
    count: int
    emit_diagnostic_sample: bool

    def to_log_dict(self) -> dict:
        payload = asdict(self.labels)
        payload["count"] = self.count
        payload["increment"] = 1
        return payload


_lock = threading.Lock()
_counters: Counter[EligibilityMetricKey] = Counter()
_diagnostic_samples: Dict[EligibilityMetricKey, int] = {}
_MAX_DIAGNOSTIC_SAMPLES_PER_KEY = 3
_MAX_DIAGNOSTIC_SAMPLE_KEYS = 100


def record_execution_eligibility_observation(
    observation: EligibilityObservation,
) -> EligibilityMetricUpdate:
    key = EligibilityMetricKey(**asdict(observation))
    with _lock:
        _counters[key] += 1
        sample_count = _diagnostic_samples.get(key, 0)
        may_add_key = key in _diagnostic_samples or len(_diagnostic_samples) < _MAX_DIAGNOSTIC_SAMPLE_KEYS
        emit_sample = may_add_key and sample_count < _MAX_DIAGNOSTIC_SAMPLES_PER_KEY
        if emit_sample:
            _diagnostic_samples[key] = sample_count + 1
        return EligibilityMetricUpdate(
            labels=key,
            count=_counters[key],
            emit_diagnostic_sample=emit_sample,
        )


def execution_eligibility_counter_snapshot() -> Tuple[Tuple[EligibilityMetricKey, int], ...]:
    with _lock:
        return tuple(
            sorted(
                _counters.items(),
                key=lambda item: tuple(str(value) for value in asdict(item[0]).values()),
            )
        )


def reset_execution_eligibility_observability() -> None:
    with _lock:
        _counters.clear()
        _diagnostic_samples.clear()
