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

from AgenticSolver.agentic.abstract import Decision, SolutionPlan, Violation
from abstract import InputTask, OutputResponse


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
    stats: Dict[str, int] = Field(default_factory=dict)
    diagnostics: List[Dict[str, Any]] = Field(default_factory=list)

    def update_from(self, results: List[Violation]) -> None:
        """
        Deterministically update stats and patches from violations.
        - This should never store sensitive data; store codes + structured hints only.
        - In a mature system, maintain a ruleset mapping diag codes -> patch templates.
        """
        pass


def propose(task: InputTask, experience: ExperienceStore) -> SolutionPlan:
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


def execute_and_validate(task: InputTask, plan: SolutionPlan) -> Decision:
    """
    Deterministic inverse_solve validator.

    Functional dependencies:
      - Inputs: task, plan.
      - plan is produced by propose().
      - policy is a static compiled artifact.

    Determinism responsibility:
      - This function MUST be deterministic (pure relative to its inputs). It MUST NOT call LLM.
      - validation is based on trace + replay.
    """
    violations: List[violations] = []

    # Stage 1: ExecutionTrace integrity

    # Stage 3: DerivedFacts replay (verification)

    # Stage 4: Policy compliance for referenced clauses

    # Stage 6: Minimality checks for escape-hatch outcomes

    ok = len(violations) == 0
    return Decision(ok=ok, violations=violations)


# ============================================================
# Main loop orchestrator
# ============================================================

def main(task: InputTask, experience: ExperienceStore) -> OutputResponse:
    """
    Orchestrator main loop.

    Args:
        task: input task
        experience: experience store

    Returns:
        response

    Key property:
      - Deterministic control flow owned by this function (trusted).
      - LLM is only used inside propose().
      - execute_and_validate() is deterministic "trusted kernel".
    """

    response = None
    # Main Propose/Validate loop
    for round_index in range(1, 5):
        # 1) LLM propose -> plan
        plan = propose(task, experience)

        # 2) Deterministic validation
        decision = execute_and_validate(task, plan)

        if decision.ok:
            return decision.response

        # 3) On failure: update experience + pass diagnostics back to next propose round
        experience.update_from(decision.verification)
        response = decision.response

    return response
