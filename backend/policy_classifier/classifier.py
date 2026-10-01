"""Policy alignment classification of a single trace event."""

from typing import Any

from policy_classifier.context import get_context, sanitize_event
from policy_classifier.prompt import get_prompt
from policy_classifier.schemas import PolicyDecision


def classify(model, trace: list[dict[str, Any]], event_id: str) -> PolicyDecision:
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

    prompt = get_prompt(
        event=event,
        role=role,
        context=context,
    )

    return model.invoke(prompt)