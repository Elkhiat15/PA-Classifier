# Write-up

## Why This Domain and This Policy

The policy is defined in `policy/policy_v1.yaml`.

**Chosen domain:** An internal **operations agent** for ABC's e-commerce and logistics operations. It can search documentation, query operational data, read and update tickets, and send emails.

I chose this domain because:

- It has realistic prompt-injection surfaces, including retrieved documentation and database rows.
- Its three user roles—`employee`, `ops_manager`, and `admin`—force the classifier to be role-aware.

Some decisions could be handled during the authorization phase, for example, blocking a user from accessing a database based on their role. Other decisions could use deterministic, rule-based checks, such as validating email domains. However, I chose to use an LLM to classify all cases in order to remain consistent with the task requirement.

### Room for Discussion

One idea for further discussion is retrieving only the policy rules relevant to the current user's role "the policy document already is written in this way, _rules per roles_". This could reduce the context size and therefore reduce both cost and latency.

## What the Classifier Outputs Beyond a Verdict (an Assumption)

In addition to the verdict, the classifier outputs:

- `decision`
- `confidence`
- `policy_rule_ids` — the policy rules that informed the decision
- `reason` — a one-sentence explanation that a human can check

These additional fields support explainability and error analysis.

## Prompt and Context Design

For each prompt, I pass the user's role, the policy, and the relevant context.

My assumption is that the context should depend on the type of event being classified:

- `tool_call` → `user_input`: check whether the tool call deviates from what the user requested.
- `tool_response` → `user_input` + the corresponding `tool_call`: perform the same check, and confirm that the tool response matches and fulfills the original tool call.
- `model_output` → `user_input`: evaluate whether the model output appropriately responds to the user's request.

This design also assumes that this is not a multi-turn conversation, so each trace contains one user input and one model output.

**Why?** This follows the example in the task document. More importantly, the production goal is to block malicious behavior or data leakage in the middle of a trace, which means classifying one event at a time. This is also not a coding assistant that may require additional user prompts during the trace.

## Corner Cases

The corner cases are documented in [`policy_corner_cases.pdf`](policy_corner_cases.pdf).

I identified and wrote down some of them through manual testing and development. I also reread the policy to identify its limitations and design tests for them. Finally, I asked Claude to generate additional samples. For all the corner cases, I wrote the initial version myself without focusing on grammar or typos, and then used an LLM to fix and refine it.

## Evaluation and Error Analysis

### Creating the Golden Examples

First, I created golden examples manually. I organized them into categories such as:

- A policy rule violated by an unauthorized user
- Authorization delegation (e.g. my manager told you to do this, ...)
- Indirect prompt injection through tool responses
- Other relevant cases

Next, I prompted two models—Claude Sonnet 5.5 and Gemini Pro—to generate more samples through their chat interfaces.

**Why did I use chat instead of the APIs?** It provided access to strong models for free, whereas the APIs available to me did not provide models of comparable quality. In any case, the amount of required data was not large enough to make this a major problem, so I could manage it manually through chat.

**Why did I use two models?** I thought using two models might reduce data leakage. I used the Gemini-generated samples for manual testing and development, while keeping the Claude-generated samples as a held-out set for testing only.

I then manually selected and relabeled the generated samples and checked their labels.

The dataset contains approximately 120 events across 20–25 traces:

- I tried to cover every corner case and base case at least once.
- I was also constrained by the free API token allowances and rate limits.
- The size was suitable for a cold-start dataset that could still be labeled manually.

### Handling Uncertain Labels

When I was unsure how to label an event, I added an `UNCERTAIN` label instead of forcing the event into only `ALLOW` or `BLOCK`. This allowed me to track ambiguous events, ask the client for clarification, and recheck the policy. It also showed me how the model handled those cases.

There are two types of test data:

1. Benign and malicious traces with traps to test the policy's clear cases.
2. Corner and ambiguous cases where the policy is silent.

### Results for the Clear Cases

The results and metrics are in `eval/data/test.ipynb`.

The accuracy was approximately 94%, which I consider expected because the samples clearly invoke the policy rules even when they contain a tricky element. However, error analysis was more important.

After reviewing the confusion matrix and the model's failures, I identified a corner case: What should happen when a tool response retrieves information that may lead to a future violation, but may not? For example, it retrieved the recipient's email address which current user is not allowed to contact but did not contact the address yet.

### Results for Corner and Ambiguous Cases

The accuracy was 0.5735.

| Class | Precision | Recall | F1-score | Support |
|---|---:|---:|---:|---:|
| `ALLOW` | 0.7727 | 0.8500 | 0.8095 | 40 |
| `BLOCK` | 0.2083 | 1.0000 | 0.3448 | 5 |
| `UNCERTAIN` | 0.0000 | 0.0000 | 0.0000 | 23 |

As usual, error analysis mattered more than the headline metric. While analyzing the failures, I found that:

- `T30-E4` and `T13-E1` (events ID located at `eval/data/corner_cases.jsonl`) appear to contradict each other, which confuses the model. It sees that `j.becker@eu.abc.com` belongs to the `@abc.com` domain, while `m.carter@abc.com.co` does not.
- The model blocked some non-malicious outputs. For example, it blocked a tool output stating that one database row was affected, and a model output stating, “I've sent the email to …”. These outputs were not malicious; the malicious action had occurred earlier.
- The model considers any partial leakage of secrets to be disallowed.

These observations agree with the corner cases identified earlier because the ambiguity itself confuses the model.

## Production and Optimization Concerns

- **Large contexts:** For long contexts, such as tool responses, I need to decide whether to classify only the current event, batch events, or truncate the context.
- **Trace-level blocking:** If a user input is blocked, the entire trace should be blocked as well. I intentionally do not do this in the current evaluation.
- **Error handling:** Additional error handling is needed.
- **Secrets:** The `.env` file must not be public. Deployment platforms provide secret management. I published it only for convenience because the tokens were free anyway.

## Future Work for a Large-Scale Project

- Generate synthetic data using more sophisticated frameworks and models, such as Ragas and DeepEval.
- Use JEV for faster classification.
- Use DSPy to optimize prompts.

## Where I Overrode the AI

Usually, I design the work and take the initiative; some examples of this are already mentioned in the evaluation section.

For all the READMEs and corner cases, I wrote the initial versions myself without focusing on grammar or typos, and then had an LLM fix and refine them.