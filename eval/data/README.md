# Evaluation Data

Description of each file in this directory:

- `claude_data.jsonl` — All data generated from Claude chats. Used to relabel, select, and adapt examples.
- `test_data.jsonl` — Selected traces from `claude_data.jsonl`, grouped into benign and malicious traces with traps that test clear cases in the policy.
- `corner_cases.jsonl` — Corner and ambiguous cases where the policy is silent.
- `dev_data.jsonl` — Traces generated from Gemini Pro chats for manual testing and prompt adaptation.
- `*_results.csv` — CSV files containing the LLM classifications used for evaluation.
- `*_mistakes.csv` — Samples where the LLM classification does not match the ground-truth label.