from enum import Enum
from typing import Dict, List, Optional, Any

from pydantic import BaseModel, Field


# ============================================================
# Core Structures
# ============================================================

class InputTask(BaseModel):
    """
    A solving task. Orchestrator passes it to propose() and execute_and_validate().
    """
    text: str


class OutputResponse(BaseModel):
    """
    The answer to be submitted.

    Lifecycle:
      - Produced by execute_and_validate().
    """
    message: str


class APICall(BaseModel):
    """
    A single API call record.

    Lifecycle:
      - proposed by LLM.
      - Called by deterministic wrapper.
    """
    id: str
    tool: str
    args: Dict[str, Any] = Field(default_factory=dict)
    expect: Optional[str] = None
    bind: Optional[str] = None
    response: Optional[Dict[str, Any]] = None
    response_hash: Optional[str] = None
    error: Optional[str] = None
    timestamp_ms: Optional[int] = None


class ExecutionTrace(BaseModel):
    """
    Deterministic trace of what execution_and_validate() actually should do via API wrappers.

    Lifecycle:
      - Created by propose() and depends on Task and on the API tools.
      - Executed deterministically.
    """
    calls: List[APICall] = Field(..., description="List of API calls")
    artifacts: Dict[str, BaseModel] = Field(default_factory=dict, description="Artifacts as entity instances")


# ============================================================
# FactQuery (For Deterministic Replay)
# ============================================================

class DataDefinitionContext(BaseModel):
    """
    Operational database is consist of tables as collection of pydantic object instances.
    It can be treated as DDL of policy entities where every object should be observable by LLM in their table.

    Lifecycle:
      - Built by deterministic wrapper code (optionally with paging aggregation).
      - Object storage mechanism is not specified but should be considered as actual snapshot of every deterministic wrapper call.
      - LLM cannot change it or create new entities in proposing process.
    """
    tables: Dict[str, List[str]] = Field(...,
                                         description="Policy entities DDL is dict of entity_name -> list of column definitions")


class FactQuery(BaseModel):
    """
    Base class for a derived fact node to select/aggregate/classify/transform values.
    FactQuery = f(Task, DataDefinitionContext, ExecutionTrace):
      - The validator must be able to replay these nodes deterministically.
      - propose() propose them based on DataDefinitionContext.
    """
    id: str
    query: str
    inputs: List[str] = Field(..., description='')  # references to earlier fact ids
    output: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Executor-populated output (must be empty in the Plan produced by propose())",
    )


# ============================================================
# Commitments (Proof Obligations)
# ============================================================

class CommitmentKind(str, Enum):
    claims = "claims"  # a set of statements from DerivedFacts that the agent considers true and relevant to the semantics of the answer.
    minimality = "minimality"  # The obligation "outcome is denied/not_found/clarification/unsupported" is not without reason, but because ok_answer is impossible.
    trace_binding = "trace_binding"  # binding facts/entities/values to specific sources in ExecutionTrace
    policy_compliance = "policy_compliance"  # доказывает “разрешено” как связь бизнес-правил из policy с разрешениями
    noninterference = "noninterference"  # proves that "nothing prohibited has leaked," such as the absence of prohibited leaks/insertions/side effects (do not disclose salary/do not include internal IDs).
    write_safety = "write_safety"  # доказательство корректности и безопасности изменяющих API (POST/PUT/PATCH/DELETE)


class PolicyRefs(BaseModel):
    """
    References to used policy clauses (by id).
    """
    rules_ids: List[str] = Field(default_factory=list, description="List of used rules ids in 'policy.py'")


class Claim(BaseModel):
    """
    An atomic claim that should be verifiable from FactQuery/ExecutionTrace/Policy.
    """
    type: str
    details: Dict[str, Any] = Field(..., description="Descriptions of details")
    fact_refs: List[str] = Field(..., description="References to FactQuery by id")
    policy_refs: PolicyRefs = Field(..., description="References to validation rule in 'policy.py'")


class Commitment(BaseModel):
    """
    A proof obligation record. The validator checks that required commitments exist and are consistent.
    - Separate "decision" from "evidence"
    - Make mistakes diagnosable
    - Prohibit "escape hatch" as a universal answer
    - Stabilize evolution by producing verifiable evidence
    """
    id: str
    kind: CommitmentKind
    claims: List[Claim] = Field(..., description="What should be considered proven.")


class Plan(BaseModel):
    """
    Bundle produced by propose():
      - execution_trace: what should be called
      - facts: what should be computed for interpretations
      - policy_refs + commitments: proof attachments
      - Creation by LLM.
      - Validation by deterministic kernel.
    """
    request: InputTask
    execution_trace: ExecutionTrace = Field(..., description="Execution trace")
    facts: List[FactQuery] = Field(..., description="Derived facts based on SQL query")
    response_template: Dict[str, Any] = Field(default_factory=dict, description="Response outcome template")
    dry_run: bool = False
    policy_refs: PolicyRefs = Field(default_factory=PolicyRefs, description="References to used policy clauses")
    commitments: List[Commitment] = Field(default_factory=list, description="Proof attachments")


# ============================================================
# 5) Violations & Decision
# ============================================================

class ViolationKind(str, Enum):
    schema_error = "SCHEMA_ERROR"
    ctx_mismatch = "CTX_MISMATCH"
    trace_integrity_fail = "TRACE_INTEGRITY_FAIL"
    missing_call = "MISSING_CALL"
    resp_hash_mismatch = "RESP_HASH_MISMATCH"
    response_contract_fail = "RESPONSE_CONTRACT_FAIL"
    public_redaction_fail = "PUBLIC_REDACTION_FAIL"
    derived_replay_fail = "DERIVED_REPLAY_FAIL"
    unknown_op = "UNKNOWN_OP"
    policy_clause_missing = "POLICY_CLAUSE_MISSING"
    policy_violation = "POLICY_VIOLATION"
    link_not_grounded = "LINK_NOT_GROUNDED"
    minimality_missing = "MINIMALITY_MISSING"
    minimality_fail = "MINIMALITY_FAIL"
    write_safety_fail = "WRITE_SAFETY_FAIL"


class Violation(BaseModel):
    kind: ViolationKind
    message: str
    path: Optional[str] = None
    details: Dict[str, Any] = Field(..., description='')


class Decision(BaseModel):
    ok: bool
    response: OutputResponse
    plan: Plan = Field(..., description="Executed and validated plan provided by propose()")
    verification: List[Violation] = Field(...,
                                          description="List of violations after verification which should be included in the experience store")
