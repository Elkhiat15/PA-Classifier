"""FastAPI backend exposing the policy alignment classifier over HTTP.

The React frontend talks to these routes (served under `/api`):

  GET  /api/health          - liveness probe
  GET  /api/policy          - the policy text the classifier enforces
  POST /api/classify        - classify one event in a trace
  POST /api/classify-trace  - classify every event in a trace
"""

from __future__ import annotations

import os
from functools import lru_cache
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from policy_classifier.classifier import classify_with_metrics
from policy_classifier.models import build_model
from policy_classifier.policy import POLICY
from policy_classifier.schemas import PolicyDecision

SUPPORTED_PROVIDERS = ("gemini", "mistral", "groq")
DEFAULT_PROVIDER = "gemini"


class ClassifyRequest(BaseModel):
    """Classify a single event identified by ``event_id`` within ``trace``."""

    trace: list[dict[str, Any]] = Field(..., min_length=1)
    event_id: str
    provider: str | None = None


class ClassifyTraceRequest(BaseModel):
    """Classify every event in ``trace``."""

    trace: list[dict[str, Any]] = Field(..., min_length=1)
    provider: str | None = None


class CallMetricsResponse(BaseModel):
    """Latency / token / cost metrics for one model call."""

    provider: str
    latency_ms: float
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    estimated_cost_usd: float


class ClassifyResponse(PolicyDecision):
    """A policy decision tied to the event it was made for."""

    event_id: str
    metrics: CallMetricsResponse | None = None


class ClassifyTraceResponse(BaseModel):
    results: list[ClassifyResponse]


app = FastAPI(
    title="Policy Alignment Classifier",
    version="0.1.0",
    description="Classify individual agent-trace events against the ABC Ops policy.",
)

# Allow the Vite dev server to call the API directly during development.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@lru_cache(maxsize=None)
def _model(provider: str):
    """Build (and cache) a chat model for ``provider``."""
    return build_model(provider)


def _resolve_provider(provider: str | None) -> str:
    resolved = provider or os.environ.get("PA_PROVIDER") or DEFAULT_PROVIDER
    if resolved not in SUPPORTED_PROVIDERS:
        raise HTTPException(
            status_code=400,
            detail=(
                f"Unsupported provider {resolved!r}. "
                f"Choose one of: {', '.join(SUPPORTED_PROVIDERS)}."
            ),
        )
    return resolved


def _classify_event(
    provider: str,
    trace: list[dict[str, Any]],
    event_id: str,
) -> ClassifyResponse:
    model = _model(provider)
    try:
        decision, metrics = classify_with_metrics(model, trace, event_id, provider)
    except StopIteration:
        raise HTTPException(
            status_code=404,
            detail=f"event_id {event_id!r} was not found in the trace.",
        ) from None
    return ClassifyResponse(
        event_id=event_id, metrics=metrics.as_dict(), **decision.model_dump()
    )


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/api/policy")
def get_policy() -> dict[str, str]:
    return {"policy": POLICY}


@app.post("/api/classify", response_model=ClassifyResponse)
def classify_event(request: ClassifyRequest) -> ClassifyResponse:
    provider = _resolve_provider(request.provider)
    return _classify_event(provider, request.trace, request.event_id)


@app.post("/api/classify-trace", response_model=ClassifyTraceResponse)
def classify_trace(request: ClassifyTraceRequest) -> ClassifyTraceResponse:
    provider = _resolve_provider(request.provider)
    event_ids = [
        event["event_id"]
        for event in request.trace
        if isinstance(event, dict) and "event_id" in event
    ]
    results = [
        _classify_event(provider, request.trace, event_id) for event_id in event_ids
    ]
    return ClassifyTraceResponse(results=results)


@app.get("/api/info")
def info() -> dict[str, str]:
    return {"service": "policy-alignment-classifier", "docs": "/docs"}


# Serve the built frontend (frontend/dist, copied to PA_STATIC_DIR at image
# build time) at "/". Mounted LAST so every /api/* route above matches first.
# When the directory is absent (e.g. running the backend standalone in dev),
# the mount is skipped and only the API routes are exposed.
_static_dir = os.environ.get("PA_STATIC_DIR", "static")
if os.path.isdir(_static_dir):
    app.mount("/", StaticFiles(directory=_static_dir, html=True), name="static")
