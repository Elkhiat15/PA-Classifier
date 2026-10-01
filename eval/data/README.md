# Evaluation data

Labelled agent-trace events for the ABC ops-agent policy (`policy/policy_v1.yaml`).

## Format
One JSON object per line (JSONL). Fields:

| field          | required | notes |
|----------------|----------|-------|
| `event_id`     | yes      | stable id; used for caching + traceability |
| `kind`         | yes      | `user_input` \| `model_output` \| `tool_call` \| `tool_response` |
| `role`         | yes      | `employee` \| `ops_manager` \| `admin` |
| `content`      | for text events | the text |
| `tool_name`    | for tool events | e.g. `send_email`, `db_query` |
| `tool_args`    | for `tool_call` | object |
| `tool_result`  | for `tool_response` | string |
| `gold_label`   | yes      | `allow` \| `violation` \| `review` |
| `gold_rule_ids`| recommended | which policy rule(s) decide it |
| `hard`         | optional | `true` if we were unsure while labelling |
| `notes`        | optional | why we labelled it this way |

## Labelling discipline (see docs/writeup.md)
- Label to the **policy as written**, not to what we wished it said.
- When the policy is silent, label `review` and record the case in
  `docs/corner_cases.md`. Never invent a rule to force a binary label.
- Every `review` case must name what we would ask the customer.

## Splits
- `cases_v1.jsonl` — the main hand-labelled set.
- `cases_hard.jsonl` — the corner cases we found while labelling (kept separate
  so we can report performance on the easy and hard sets honestly).