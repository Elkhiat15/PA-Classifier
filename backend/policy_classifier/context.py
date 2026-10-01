"""Trace event sanitization and context extraction."""

from typing import Any


def sanitize_event(event: dict[str, Any]) -> dict[str, Any]:
    return {
        key: value
        for key, value in event.items()
        if key != "expected_verdict"
    }


def get_context(
    trace: list[dict[str, Any]],
    event: dict[str, Any],
) -> list[dict[str, Any]]:

    event_type = event["event_type"]

    # user_input -> no context
    if event_type == "user_input":
        return []

    # There is exactly one user_input per trace
    user_input = next(
        e for e in trace
        if e.get("event_type") == "user_input"
    )

    user_input = sanitize_event(user_input)
    # tool_call -> user_input
    if event_type == "tool_call":

        return [user_input]

    # tool_response -> user_input + corresponding tool_call
    if event_type == "tool_response":
        event_index = trace.index(event)

        tool_call = trace[event_index - 1]
        tool_call = sanitize_event(tool_call)
        return [user_input, tool_call]

    # model_output -> user_input
    if event_type == "model_output":
        return [user_input]

    return []