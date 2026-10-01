"""Policy alignment classification of a single trace event."""

from typing import Any

from policy_classifier.context import get_context, sanitize_event
from policy_classifier.metrics import CallMetrics, measure
from policy_classifier.prompt import get_prompt
from policy_classifier.schemas import PolicyDecision


def _build_prompt(trace: list[dict[str, Any]], event_id: str) -> str:
    """Locate the event in the trace and render the classifier prompt."""
    # The first object in the trace contains the trace-level metadata.
    trace_metadata = trace[0]

    role = trace_metadata["role"]

    # Find the requested event.
    event = next(
        event
        for event in trace
        if event.get("event_id") == event_id
    )

    context = get_context(trace, event)
    event = sanitize_event(event)

    return get_prompt(
        event=event,
        role=role,
        context=context,
    )


def classify(model, trace: list[dict[str, Any]], event_id: str) -> PolicyDecision:
    prompt = _build_prompt(trace, event_id)
    return model.invoke(prompt)


def classify_with_metrics(
    model,
    trace: list[dict[str, Any]],
    event_id: str,
    provider: str,
) -> tuple[PolicyDecision, CallMetrics]:
    """Classify one event and return the decision plus call metrics.

    ``classify`` is the plain path (used by tests/eval); this variant adds
    latency/token/cost capture and is what the HTTP API uses.
    """
    prompt = _build_prompt(trace, event_id)
    decision, metrics = measure(provider, model.invoke, prompt)
    return decision, metrics
