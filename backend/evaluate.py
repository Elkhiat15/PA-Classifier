"""Evaluation script for the policy alignment classifier.

Loads the test dataset (a list of event traces), runs the plain
(no-metrics) classifier on every event of every trace, and streams the
results to ``test_results.csv`` in batches.

The resulting dataframe has one row per event and contains every flattened
trace/event field plus the classifier answer fields
(``decision``, ``confidence``, ``policy_rule_ids``, ``reasoning``).

Run from the ``backend/`` directory::

    python evaluate.py
"""

from __future__ import annotations

import json
import re
import sys
import time
from pathlib import Path

import pandas as pd

# ---------------------------------------------------------------------------
# Make the backend `policy_classifier` package importable when this file is
# executed directly (e.g. `python evaluate.py` from inside `backend/`).
# ---------------------------------------------------------------------------
BACKEND_DIR = Path(__file__).resolve().parent
REPO_ROOT = BACKEND_DIR.parent
sys.path.insert(0, str(BACKEND_DIR))

from policy_classifier import build_model, classify  # noqa: E402

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
DATA_PATH = REPO_ROOT / "eval" / "data" / "corner_cases.jsonl"
OUT_PATH = REPO_ROOT / "eval" / "data" / "corner_cases_test_results.csv"

PROVIDER = "gemini"
BATCH_SIZE = 5            # save + pause after this many requests
BATCH_DELAY_SECONDS = 0.5

# Column order for the output dataframe: flattened metadata + event fields,
# followed by the classifier answers.
COLUMNS = [
    "category",
    "trace_id",
    "role",
    "event_id",
    "event_type",
    "payload",
    "expected_verdict",
    "decision",
    "confidence",
    "policy_rule_ids",
    "reasoning",
]


def _load_json(path: Path):
    """Load JSON, tolerating trailing commas (the data files aren't strict)."""
    text = path.read_text(encoding="utf-8")
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        # Remove a comma that appears right before a closing ] or }.
        cleaned = re.sub(r",(\s*[\]}])", r"\1", text)
        return json.loads(cleaned)


def _save_batch(records: list[dict], *, header: bool) -> None:
    """Append a batch of records to the CSV, writing the header once."""
    df = pd.DataFrame(records, columns=COLUMNS)
    df.to_csv(
        OUT_PATH,
        mode="w" if header else "a",
        header=header,
        index=False,
    )


def main() -> int:
    data = _load_json(DATA_PATH)

    model = build_model(PROVIDER)

    batch: list[dict] = []
    request_count = 0
    wrote_header = False

    # Loop over the traces, then over the events inside each trace.
    for trace in data:
        metadata = trace[0]
        category = metadata.get("category")
        trace_id = metadata.get("trace_id")
        role = metadata.get("role")

        for event in trace[1:]:
            event_id = event["event_id"]

            try:
                decision = classify(model, trace, event_id)
                answer = {
                    "decision": decision.decision,
                    "confidence": decision.confidence,
                    "policy_rule_ids": ";".join(decision.policy_rule_ids),
                    "reasoning": decision.reasoning,
                }
            except Exception as exc:  # keep the run going on transient errors
                print(f"[warn] {event_id} failed: {exc}", file=sys.stderr)
                answer = {
                    "decision": None,
                    "confidence": None,
                    "policy_rule_ids": "",
                    "reasoning": f"ERROR: {exc}",
                }

            batch.append(
                {
                    "category": category,
                    "trace_id": trace_id,
                    "role": role,
                    "event_id": event_id,
                    "event_type": event.get("event_type"),
                    "payload": event.get("payload"),
                    "expected_verdict": event.get("expected_verdict"),
                    **answer,
                }
            )
            request_count += 1

            # After every BATCH_SIZE requests: pause, then persist the batch.
            if request_count % BATCH_SIZE == 0:
                time.sleep(BATCH_DELAY_SECONDS)
                _save_batch(batch, header=not wrote_header)
                wrote_header = True
                batch.clear()
                print(f"[info] saved {request_count} results -> {OUT_PATH}")

    # Flush any remaining events that did not fill a full batch.
    if batch:
        _save_batch(batch, header=not wrote_header)
        wrote_header = True
        print(f"[info] saved {request_count} results -> {OUT_PATH}")

    print(f"[done] {request_count} events written to {OUT_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())