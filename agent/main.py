"""
Conceptual AI agent runner (external orchestrator).

Goal:
  - propose() is LLM-driven (Codex/Codex CLI), producing (response, cert).
  - validate() is deterministic (trusted kernel), verifying cert.
  - The main loop is external (Python), enforcing budgets, retries, and safety.

This file focuses on MAIN LOOP shape and data flow.
"""

from __future__ import annotations

from typing import Any, Dict, List

from pydantic import BaseModel, Field

from abstract import InputTask, OutputResponse

# For this conceptual example, we only reference these names for typing.
# Replace with real imports from your validator module.
validate = Any
Verification = Any
Certificate = Any
Plan = Any


# ============================================================
# Task & Snapshot & Experience (orchestrator-owned)
# ============================================================


class ExperiencePatch(BaseModel):
    """
    A structured patch / heuristic distilled from previous diagnostics.

    Key idea:
      - Experience is NOT raw entity data.
      - It stores conditions + fix hints (deterministic knowledge) to help propose().
      - Stored/updated by orchestrator deterministically based on validator diagnostics.
      - Consumed by propose() (LLM) as a hint.
    """
    patch_id: str
    applies_when: Dict[str, Any] = Field(..., description="Applies when")  # e.g. {"is_public": True, "outcome": "..."}
    guidance: str  # NL guidance for propose (still safe, not a rule change)
    severity: int = 1


class ExperienceStore(BaseModel):
    """
    Experience store used to reduce human involvement.
      - Update logic is deterministic based on diagnostics.
      - 'guidance' may be NL, but it is curated by deterministic rules/templates.
    """
    patches: List[ExperiencePatch] = Field(default_factory=list)
    diag_stats: Dict[str, int] = Field(default_factory=dict)
    diagnostics: List[Dict[str, Any]] = Field(default_factory=list)

    def update_from(self, result: Verification) -> None:
        """
        Deterministically update stats and patches from validator diagnostics.

        Note:
          - This should never store sensitive data; store codes + structured hints only.
          - In a mature system, you'd maintain a ruleset mapping diag codes -> patch templates.
        """
        pass


def propose(task: InputTask, experience: ExperienceStore) -> Plan:
    """
    LLM-driven propose function (Codex/Codex CLI).

    Determinism responsibility:
      - Not deterministic. It may vary across runs.
      - Must output a Plan that can be validated by deterministic kernel.

    Functional dependency:
      - Depends on task, API calls, and experience hints.
      - Must embed trace/facts/policy refs/commitments sufficient for deterministic validation.
    """
    pass


# ============================================================
# Main loop orchestrator
# ============================================================

def main(task: InputTask, experience: ExperienceStore) -> OutputResponse:
    """
    External orchestrator main loop.

    Args:
        task: input task
        experience: experience store

    Returns:
        response

    Key property:
      - Deterministic control flow owned by this function (trusted).
      - LLM is only used inside propose().
      - validate() is deterministic "trusted kernel".
    """

    response = None
    # Main Propose/Validate loop
    for round_index in range(1, 5):
        # 1) LLM propose -> plan
        plan = propose(task, experience)

        # 2) Deterministic validation
        decision = validate(task, plan)

        if decision.ok:
            return decision.response

        # 3) On failure: update experience + pass diagnostics back to next propose round
        experience.update_from(decision.verification)
        response = decision.response

    return response
