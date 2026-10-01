# PA-Classifier — Policy Alignment Classifier

Reads **one agent-trace event** and decides whether a policy permits it.
Four event kinds: `user_input`, `model_output`, `tool_call`, `tool_response`.
Domain (chosen): an internal **ops agent** for ABC (e-commerce + logistics).

This is an LLM-through-prompting classifier. No fine-tuning.

- Policy: [`policy/policy_v1.yaml`](policy/policy_v1.yaml)
- Reasoning: [`docs/writeup.md`](docs/writeup.md)
- Corner cases: [`docs/corner_cases.md`](docs/corner_cases.md)
- Assumptions: [`docs/assumptions.md`](docs/assumptions.md)

> Status: **scaffold**. File layout, package setup, and the full frontend are in
> place and runnable in mock mode. Backend modules are typed stubs raising
> `NotImplementedError`; fill them in next. See `TODO`s in each file.

---

## One command that runs it

The demo runs with **no API keys** thanks to a mock layer. From a fresh clone:

```bash
make dev
```

This installs the Python env (Poetry) and the frontend deps, then starts the
FastAPI server (:8000) and the Vite dev server (:5173). Open
<http://localhost:5173>. The page defaults to **mock** source; switch the
`source` dropdown to **live API** once the backend endpoints are implemented.

If you prefer to do it by hand:

```bash
# backend
poetry install
cp .env.example .env            # fill in a key only if you want live calls
poetry run pa-serve             # http://127.0.0.1:8000

# frontend (new terminal)
cd frontend && npm install && npm run dev   # http://localhost:5173
```

## How the frontend connects to the logic

This is the part that matters, so it is worth stating plainly:

```
React (browser)
  └─ src/api/client.ts     → fetch("/api/...")      # the ONLY network seam
        └─ Vite dev proxy   → http://127.0.0.1:8000
              └─ FastAPI (src/pa_classifier/api/app.py)
                    └─ Classifier (src/pa_classifier/classifier.py)
                          ├─ Policy      (src/pa_classifier/policy.py)
                          ├─ Prompts     (src/pa_classifier/prompts.py)
                          ├─ Guards      (src/pa_classifier/guards.py)
                          └─ LLMClient   (src/pa_classifier/llm/*)
```

Key points:
- **The browser never calls a model.** No keys in the client. The API does the
  work; the frontend only renders verdicts.
- **One seam.** `frontend/src/hooks/useClassifier.ts` is the single integration
  point. It switches between `api/client.ts` (live) and `api/mock.ts` (offline).
- **One contract.** Wire types live in `frontend/src/api/types.ts` and mirror
  the backend pydantic models in `src/pa_classifier/models.py` and
  `src/pa_classifier/api/schemas.py`.
- **Dev proxy, not CORS gymnastics.** `frontend/vite.config.ts` proxies `/api`
  to the backend, so the same code works in dev and prod (same origin).

### Endpoints the page expects
| method | path                   | purpose |
|--------|------------------------|---------|
| GET    | `/api/health`          | provider/model/prompt status |
| GET    | `/api/policy`          | active policy, for display |
| POST   | `/api/classify`        | classify one event |
| POST   | `/api/classify/batch`  | classify many (demo table) |
| GET    | `/api/eval/summary`    | last eval metrics (honest numbers) |

## Repo layout

```
policy/                 versioned policy YAML (external config)
src/pa_classifier/       the classifier package (Poetry)
  models.py              TraceEvent, Verdict, Label, Evidence
  config.py              env-backed settings (provider/model/prompt)
  policy.py              load + render policy
  prompts.py             system/user prompt + strict JSON parse
  guards.py              optional high-precision pre-filters
  classifier.py          one event in → one Verdict out
  cli.py                 pa-classify
  llm/                   provider adapters + factory (openai/anthropic/ollama)
  api/                   FastAPI app + wire schemas
eval/                    labelled data + metrics + runner (pa-eval)
frontend/                Vite + React single page (the demo)
tests/                   unit tests + a deterministic fake LLM client
docs/                    writeup, corner cases, assumptions
```

## Evidence & evaluation

```bash
poetry run pa-eval --data eval/data/cases_v1.jsonl --out eval/results/run-001
```

We report accuracy **plus** violation recall/precision, the `review` rate, and
the parse-failure rate, and we keep the hard cases in a separate file so easy
numbers cannot hide hard failures. Rationale in `docs/writeup.md` §7.

## Assumptions
See [`docs/assumptions.md`](docs/assumptions.md). The load-bearing ones: the
output is an auditable verdict (not a bare label); there is a third `review`
label; classification is per-event; the policy is external config; and the demo
ships a mock so it runs with no keys.