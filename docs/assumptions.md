# Assumptions log

The brief says: where it does not decide something, make the most realistic
assumption, write it down, and keep going. This is that list. Each assumption
names the decision, the reason, and what would force a revisit.

| # | Assumption | Why | Revisit if |
|---|-----------|-----|-----------|
| A1 | Output is an **auditable verdict** (label + evidence + provenance), not a bare label. | A guardrail a human cannot audit will not be trusted or debuggable. | The consumer only needs a boolean and cost/latency dominates. |
| A2 | Add a `review` label beyond `allow`/`violation`. | The policy is genuinely silent on real events; a forced binary hides that. | A downstream system cannot handle a third state and demands binary. |
| A3 | Classification is **per-event**, mostly stateless; role + tool args travel on the event. | A guardrail sits on the request path; full-conversation context is not guaranteed. | Attachments/intent cases (CC-04, CC-05) turn out to dominate. |
| A4 | The policy is **external config** (`policy/*.yaml`), not baked into the prompt. | Makes the classifier policy-agnostic and the policy reviewable by non-engineers. | A policy needs logic YAML cannot express cleanly. |
| A5 | `temperature=0` but outputs are **cached** per (event_id, model, prompt_version). | Temperature 0 is not truly deterministic; caching makes runs reproducible and free. | A model/provider ignores temperature or caching becomes stale. |
| A6 | "Enough cases" = a hand-labelled set of ~100 events, with a separate hard set. | Enough to be honest about failure modes without pretending to statistical power. | Results are used to make a launch decision, not a demo. |
| A7 | Provider is pluggable; default demo runs on a **mock** so no keys are needed. | Reviewers must be able to run it; keys/tokens are a barrier. | The reviewer wants real numbers; then they set `.env` and use the live toggle. |
| A8 | The frontend talks to the backend only over `/api/*` (never directly to a model). | Keys must never live in the browser; same code works in dev and prod. | Never — this is a security invariant, not a preference. |
| A9 | One React page is enough; "we are not scoring CSS." | The brief says so explicitly. | It does not. |