"""Structured output schema for policy decisions."""

from typing import Literal

from pydantic import BaseModel, Field

PolicyRuleID = Literal[
    "OPS-001",
    "OPS-002",
    "OPS-003",
    "OPS-004",
    "OPS-005",
    "OPS-006",
    "OPS-007",
    "OPS-008",
]


class PolicyDecision(BaseModel):
    decision: Literal["ALLOW", "BLOCK", "UNCERTAIN"]
    confidence: float = Field(ge=0.0, le=1.0)
    policy_rule_ids: list[PolicyRuleID] = Field(default_factory=list)
    reasoning: str