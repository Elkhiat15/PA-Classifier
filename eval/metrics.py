"""Metric computation.

STUB. Report honest numbers. Accuracy alone hides the failure mode that matters
(a missed violation). We will report, at minimum:

  - overall accuracy
  - per-label confusion matrix
  - violation recall (did we catch the bad events?) and violation precision
    (how often we cried wolf?)
  - a "REVIEW" rate, because a classifier that dumps everything to REVIEW is
    useless even at high accuracy
  - parse-failure rate (how often the model did not return valid JSON)

TODO: implement `compute_metrics(records)`.
"""

from __future__ import annotations

from typing import Any


def compute_metrics(records: list[dict[str, Any]]) -> dict[str, Any]:
    """Compute the metric bundle from per-event records.

    TODO: implement. `records` carry gold_label, pred_label, kind, rule_id, etc.
    """
    raise NotImplementedError("metrics.compute_metrics is not implemented yet")