"""Evaluation entry point (`pa-eval`).

STUB. Loads labelled cases, runs the classifier, writes artifacts, prints a
summary. Implement later.

Usage (planned):
  poetry run pa-eval --data eval/data/cases_v1.jsonl --out eval/results/run-001

Assumptions (documented):
  - Outputs are CACHED per (event_id, model, prompt_version) so a rerun is free
    and reproducible despite temperature=0 not being truly deterministic.
  - We record raw model output for every case, so failures can be inspected
    after the fact instead of guessed at.
"""

from __future__ import annotations

import argparse
from pathlib import Path


def run(data_path: Path, out_dir: Path, model: str | None = None) -> dict:
    """Run the classifier over the dataset and write artifacts.

    TODO: implement.
    """
    raise NotImplementedError("run_eval.run is not implemented yet")


def main() -> int:
    """CLI entry point. TODO: wire argparse to `run`."""
    parser = argparse.ArgumentParser(prog="pa-eval")
    parser.add_argument("--data", type=Path, default=Path("eval/data/cases_v1.jsonl"))
    parser.add_argument("--out", type=Path, default=Path("eval/results/latest"))
    parser.add_argument("--model", type=str, default=None)
    args = parser.parse_args()

    raise NotImplementedError(f"run_eval not implemented (args={args})")


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())