"""phaseledger: local-first phase ledger with measurer-first advances."""

from .measure import VERDICTS, MeasureResult, measure
from .ledger import DEFAULT_PHASES, PhaseLedger, PhaseState

__all__ = [
    "VERDICTS",
    "MeasureResult",
    "measure",
    "DEFAULT_PHASES",
    "PhaseLedger",
    "PhaseState",
]

__version__ = "0.1.0"
