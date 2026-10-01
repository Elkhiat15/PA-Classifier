"""Evaluation harness.

STUB. Separate from `src/pa_classifier` on purpose: evaluation is a consumer of
the classifier, not part of it, so a reviewer can run the model without the
harness and the harness without a server.

Layout:
  eval/data/       labelled cases (jsonl)
  eval/run_eval.py entry point (`pa-eval`)
  eval/metrics.py  metric computation
  eval/results/    run artifacts (per-event outputs + summary)
"""