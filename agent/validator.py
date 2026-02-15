from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import (
    Any,
    Callable,
    Dict,
    List,
    Literal,
    Mapping,
    Optional,
    Sequence,
    Tuple,
    Union,
)

from pydantic import BaseModel, Field


# ============================================================
# PolicyClauses (Static, Compiled from Wiki)
# ============================================================

class Condition(BaseModel):
    """
    Minimal condition AST.
    One of:
      - eq, ne, present, in, not_in, any, all, not
    Paths are simple dotted references resolved from Env.

    Example:
      {"eq": ["ctx.is_public", True]}
      {"present": "response.message"}
      {"any": [{"eq": ["ctx.is_public", True]}, {"eq": ["ctx.level", 3]}]}
    """
    eq: Optional[Tuple[str, Any]] = None
    ne: Optional[Tuple[str, Any]] = None
    present: Optional[str] = None
    in_: Optional[Tuple[str, List[Any]]] = Field(default=None, alias="in")
    not_in: Optional[Tuple[str, List[Any]]] = None
    any: Optional[List["Condition"]] = None
    all: Optional[List["Condition"]] = None
    not_: Optional["Condition"] = Field(default=None, alias="not")


class ClauseKind(str, Enum):
    invariant = "invariant"  # contract-level invariants
    require = "require"  # must hold
    forbid = "forbid"  # must NOT happen
    rule = "rule"  # derive / set (optional; usually used in DF, not in validator)


class Requirement(BaseModel):
    """
    Simple requirement language used by clauses.
    """
    condition: Condition
    message: str


class PolicyClause(BaseModel):
    """
    A compiled rule.

    Functional dependency:
      - Depends on Wiki only (static), not on TaskText.
      - Applicability depends on Env at validation time.

    Determinism responsibility:
      - Compilation is offline (human/tooling).
      - Evaluation is deterministic.
    """
    id: str
    kind: ClauseKind
    when: Optional[Condition] = None
    require: List[Requirement] = Field(default_factory=list)
    forbid: List[Requirement] = Field(default_factory=list)


class PolicyProgram(BaseModel):
    """
    Collection of clauses (compiled policies).
    """
    version: str
    clauses: List[PolicyClause]


# ============================================================
# 3) DerivedFacts and Ops (Deterministic Replay)
# ============================================================

class FactKind(str, Enum):
    select = "select"
    normalize = "normalize"
    classify = "classify"
    join = "join"
    compute = "compute"


class DerivedFactBase(BaseModel):
    """
    Base class for a derived fact node to select/aggregate/classify/transform values.
    DerivedFacts = f(PolicyClauses, Ctx, ExecutionTrace, Task)

    Determinism responsibility:
      - The validator must be able to replay these nodes deterministically.
      - solve() (LLM) may propose them, but inverse_solve() verifies them by replay.
    """
    id: str
    kind: FactKind
    op: str
    inputs: List[str] = Field(..., description='')  # references to earlier fact ids
    output: Dict[str, Any] = Field(..., description='')


class SelectFact(DerivedFactBase):
    kind: Literal[FactKind.select] = FactKind.select
    op: Literal["json_select"] = "json_select"
    call_id: str
    json_pointer: str


class NormalizeFact(DerivedFactBase):
    kind: Literal[FactKind.normalize] = FactKind.normalize
    op: Literal["norm_whitespace", "norm_person_name", "norm_project_name"]


class ClassifyFact(DerivedFactBase):
    kind: Literal[FactKind.classify] = FactKind.classify
    op: Literal["data_class_from_fields"]


class JoinFact(DerivedFactBase):
    kind: Literal[FactKind.join] = FactKind.join
    op: Literal["join_by_id"]


class ComputeFact(DerivedFactBase):
    kind: Literal[FactKind.compute] = FactKind.compute
    op: Literal["compute_links_minimal"]


DerivedFact = Union[SelectFact, NormalizeFact, ClassifyFact, JoinFact, ComputeFact]


class DerivedFacts(BaseModel):
    """
    Ordered list of derived facts; evaluated sequentially.
    """
    facts: List[DerivedFact] = Field(..., description='List of facts')


# ============================================================
# 4) Commitments (Proof Obligations)
# ============================================================

class CommitmentKind(str, Enum):
    claims = "claims"
    minimality = "minimality"
    trace_binding = "trace_binding"
    policy_compliance = "policy_compliance"
    link_grounding = "link_grounding"
    noninterference = "noninterference"
    write_safety = "write_safety"


class Claim(BaseModel):
    """
    An atomic claim that should be verifiable from DF/ET/Policy.
    """
    type: str
    details: Dict[str, Any] = Field(..., description='')
    supported_by_fact_ids: List[str] = Field(..., description='')
    supported_by_clause_ids: List[str] = Field(..., description='')


class AlternativeCheck(BaseModel):
    """
    For minimality: prove certain alternatives are impossible.
    """
    outcome: Any
    status: Literal["impossible", "not_attempted"]
    reason_clause_id: Optional[str] = None
    explanation: Optional[str] = None


class Commitment(BaseModel):
    """
    A proof obligation record. The validator checks that required commitments exist and are consistent.
    """
    id: str
    kind: CommitmentKind
    claims: List[Claim] = Field(..., description="List of claims")
    for_outcome: Optional[Any] = None
    checked_alternatives: List[AlternativeCheck] = Field(..., description="List of checked alternatives")


class PolicyRefs(BaseModel):
    """
    References to used policy clauses (by id).
    """
    used_clause_ids: List[str] = Field(..., description="List of used clause ids")


class Certificate(BaseModel):
    """
    Bundle produced by solve() (LLM + wrappers):
      - response: proposed answer to /respond
      - execution_trace: what was called
      - derived_facts: computed interpretations
      - policy_refs + commitments: proof attachments

    Determinism responsibility:
      - Creation: LLM + deterministic wrappers (trace).
      - Validation: deterministic kernel (inverse_solve).
    """
    pc_version: str
    task_text: str
    response: Response
    execution_trace: ExecutionTrace
    derived_facts: DerivedFacts
    policy_refs: PolicyRefs = Field(default_factory=PolicyRefs)
    commitments: List[Commitment] = Field(default_factory=list)


# ============================================================
# 5) Diagnostics & Result Types
# ============================================================

class DiagCode(str, Enum):
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


class Diagnostic(BaseModel):
    code: DiagCode
    message: str
    path: Optional[str] = None
    details: Dict[str, Any] = Field(..., description='')


class VerificationResult(BaseModel):
    ok: bool
    diagnostics: List[Diagnostic] = Field(..., description="List of diagnostics")


# ============================================================
# 6) Deterministic Ops Registry (Replay Engine)
# ============================================================

@dataclass(frozen=True)
class OpContext:
    """
    Inputs available to deterministic ops.

    Note:
      - Ops MUST be pure functions. No API calls, no randomness.
    """
    ctx: ContextIdentity
    trace_calls: Dict[str, APICallRecord]
    response: Response


OpFn = Callable[[OpContext, Dict[str, Any], List[Dict[str, Any]], DerivedFactBase], Dict[str, Any]]


# ============================================================
# 8) Validation Workflow (inverse_solve)
# ============================================================

def replay_derived_facts(
        ctx: ContextIdentity,
        response: Response,
        trace: ExecutionTrace,
        derived: DerivedFacts,
        ops: Mapping[str, OpFn],
) -> Tuple[Dict[str, Dict[str, Any]], List[Diagnostic]]:
    """
    Deterministically replay DerivedFacts and verify each node's output.

    What is verified:
      - All inputs reference earlier fact ids.
      - The op exists in ops registry.
      - The computed output matches node.output (deep-equal).

    What is NOT done:
      - No API calls.
      - No LLM calls.
    """
    diags: List[Diagnostic] = []
    call_map = {c.id: c for c in trace.calls}
    oc = OpContext(ctx=ctx, trace_calls=call_map, response=response)

    df_outputs: Dict[str, Dict[str, Any]] = {}

    for node in derived.facts:
        # Validate op exists
        if node.op not in ops:
            diags.append(Diagnostic(
                code=DiagCode.unknown_op,
                message=f"Unknown op '{node.op}'",
                path=f"derived_facts.facts[{node.id}].op",
            ))
            continue

        # Collect inputs
        inputs: List[Dict[str, Any]] = []
        missing_inputs = [fid for fid in node.inputs if fid not in df_outputs]
        if missing_inputs:
            diags.append(Diagnostic(
                code=DiagCode.derived_replay_fail,
                message="Derived fact references missing inputs",
                path=f"derived_facts.facts[{node.id}].inputs",
                details={"missing": missing_inputs},
            ))
            continue

        inputs = [df_outputs[fid] for fid in node.inputs]

        # Replay
        try:
            computed = ops[node.op](oc, build_env(ctx, response, df_outputs), inputs, node)  # type: ignore[arg-type]
        except Exception as e:
            diags.append(Diagnostic(
                code=DiagCode.derived_replay_fail,
                message=f"Replay failed for node {node.id}: {e}",
                path=f"derived_facts.facts[{node.id}]",
            ))
            continue

        # Compare
        if computed != node.output:
            diags.append(Diagnostic(
                code=DiagCode.derived_replay_fail,
                message=f"Derived output mismatch for node {node.id}",
                path=f"derived_facts.facts[{node.id}].output",
                details={"expected": node.output, "computed": computed},
            ))
            continue

        df_outputs[node.id] = computed

    return df_outputs, diags


def verify_trace_integrity(trace: ExecutionTrace, expected_ctx: ContextIdentity) -> List[Diagnostic]:
    """
    Verify ExecutionTrace integrity (hashes, ctx match, response hash checks).

    Determinism responsibility:
      - Deterministic checks only.
      - Does NOT call external API.
    """
    diags: List[Diagnostic] = []

    # Context hash match
    if trace.ctx.ctx_hash != expected_ctx.ctx_hash:
        diags.append(Diagnostic(
            code=DiagCode.ctx_mismatch,
            message="ExecutionTrace ctx_hash does not match expected ctx_hash",
            path="execution_trace.ctx.ctx_hash",
            details={"expected": expected_ctx.ctx_hash, "got": trace.ctx.ctx_hash},
        ))

    # Verify response hashes when response is embedded
    for call in trace.calls:
        if call.response is not None:
            computed = sha256_hex(call.response)
            if call.response_hash and computed != call.response_hash:
                diags.append(Diagnostic(
                    code=DiagCode.resp_hash_mismatch,
                    message=f"Response hash mismatch for call {call.id}",
                    path=f"execution_trace.calls[{call.id}].response_hash",
                    details={"expected": call.response_hash, "computed": computed},
                ))
        else:
            # No embedded response => cannot replay DF nodes that depend on it.
            # Not always fatal, but it limits verifiability.
            pass

    return diags


def verify_policy_refs_and_compliance(policy: PolicyProgram, used_clause_ids: Sequence[str], env: Dict[str, Any]) \
        -> List[Diagnostic]:
    """
    Verify:
      - All referenced clauses exist.
      - Each referenced clause is applicable (when) and satisfied (require/forbid).

    Note:
      - This is NOT identical to "response contract checks".
      - Contract checks validate protocol invariants; policy checks validate authorization and rules.
    """
    diags: List[Diagnostic] = []
    clause_map = policy.clause_by_id()

    for cid in used_clause_ids:
        clause = clause_map.get(cid)
        if clause is None:
            diags.append(Diagnostic(
                code=DiagCode.policy_clause_missing,
                message=f"Referenced policy clause not found: {cid}",
                path="certificate.policy_refs.used_clause_ids",
                details={"clause_id": cid},
            ))
            continue

        if not clause_applicable(env, clause):
            diags.append(Diagnostic(
                code=DiagCode.policy_violation,
                message=f"Referenced policy clause is not applicable under current env: {cid}",
                path=f"policy.{cid}.when",
            ))
            continue

        # Requirements
        for req in clause.require:
            if not cond_eval(env, req.condition):
                diags.append(Diagnostic(
                    code=DiagCode.policy_violation,
                    message=f"Policy requirement failed ({cid}): {req.message}",
                    path=f"policy.{cid}.require",
                    details={"clause_id": cid},
                ))

        # Forbids: condition must be False
        for fb in clause.forbid:
            if cond_eval(env, fb.condition):
                diags.append(Diagnostic(
                    code=DiagCode.policy_violation,
                    message=f"Policy forbid violated ({cid}): {fb.message}",
                    path=f"policy.{cid}.forbid",
                    details={"clause_id": cid},
                ))

    return diags


def verify_link_grounding(response: Response, trace: ExecutionTrace, df_outputs: Dict[str, Dict[str, Any]]) -> List[
    Diagnostic]:
    """
    Verify that each response.link is grounded in ExecutionTrace artifacts.

    Minimal deterministic rule:
      - Each link(kind,id) must appear in trace.artifacts.
    """
    diags: List[Diagnostic] = []
    artifact_set = {(a.kind, a.id) for a in trace.artifacts}

    for i, link in enumerate(response.links):
        if (link.kind, link.id) not in artifact_set:
            diags.append(Diagnostic(
                code=DiagCode.link_not_grounded,
                message="Link not grounded in trace artifacts",
                path=f"response.links[{i}]",
                details={"kind": link.kind.value, "id": link.id},
            ))

    return diags


def verify_minimality(response: Response, commitments: Sequence[Commitment], policy: PolicyProgram,
                      env: Dict[str, Any]) -> List[Diagnostic]:
    """
    Minimality checks for escape-hatch outcomes.

    Deterministic rule:
      - If outcome is escape-hatch, there must be at least one commitment(kind=minimality, for_outcome=outcome).
      - That commitment must mark ok_answer as "impossible" with a known reason_clause_id
        (or explicitly "not_attempted" if you accept weaker proofs).
      - The reason clause must exist and be applicable in the current env.

    This prevents trivial "deny/clarify always" behavior.
    """
    diags: List[Diagnostic] = []
    mins = [c for c in commitments if c.kind == CommitmentKind.minimality and c.for_outcome == response.outcome]

    if not mins:
        diags.append(Diagnostic(
            code=DiagCode.minimality_missing,
            message="Missing minimality commitment for escape-hatch outcome",
            path="certificate.commitments",
            details={"outcome": response.outcome.value},
        ))
        return diags

    clause_map = policy.clause_by_id()

    # Require at least a mention of ok_answer alternative
    has_ok_answer_alt = False
    for c in mins:
        for alt in c.checked_alternatives:
            if alt.outcome == Outcome.ok_answer:
                has_ok_answer_alt = True
                if alt.status != "impossible":
                    diags.append(Diagnostic(
                        code=DiagCode.minimality_fail,
                        message="ok_answer alternative must be marked impossible (or tighten validator rules)",
                        path=f"commitments[{c.id}].checked_alternatives",
                    ))
                    continue
                if not alt.reason_clause_id:
                    diags.append(Diagnostic(
                        code=DiagCode.minimality_fail,
                        message="Missing reason_clause_id for impossible ok_answer alternative",
                        path=f"commitments[{c.id}].checked_alternatives",
                    ))
                    continue
                clause = clause_map.get(alt.reason_clause_id)
                if clause is None:
                    diags.append(Diagnostic(
                        code=DiagCode.minimality_fail,
                        message="Minimality reason clause id not found",
                        path=f"commitments[{c.id}].checked_alternatives",
                        details={"reason_clause_id": alt.reason_clause_id},
                    ))
                    continue
                if not clause_applicable(env, clause):
                    diags.append(Diagnostic(
                        code=DiagCode.minimality_fail,
                        message="Minimality reason clause not applicable under current env",
                        path=f"policy.{alt.reason_clause_id}.when",
                    ))

    if not has_ok_answer_alt:
        diags.append(Diagnostic(
            code=DiagCode.minimality_fail,
            message="Minimality commitment must consider ok_answer alternative",
            path="certificate.commitments",
        ))

    return diags


def validate(task: str, ctx: ContextIdentity, cert: Certificate, policy: PolicyProgram,
             ops: Mapping[str, OpFn] = DEFAULT_OPS) -> VerificationResult:
    """
    Deterministic inverse_solve validator.

    Functional dependencies:
      - Inputs: (task_text, ctx) are the authoritative task + identity context from wrappers.
      - cert is produced by solve() (LLM + wrappers).
      - policy is a static compiled artifact (from Wiki).
      - ops is deterministic library for replaying DerivedFacts.

    Determinism responsibility:
      - This function MUST be deterministic (pure relative to its inputs).
      - It MUST NOT call LLM.
      - It SHOULD NOT call ERC3 API; validation is based on trace + replay.
    """
    diags: List[Diagnostic] = []

    # Stage 0: Schema / basic consistency
    if cert.task_text != task.text:
        diags.append(Diagnostic(
            code=DiagCode.schema_error,
            message="Certificate task_text does not match authoritative task_text",
            path="certificate.task_text",
        ))

    if cert.pc_version != policy.version:
        diags.append(Diagnostic(
            code=DiagCode.schema_error,
            message="Certificate pc_version does not match validator policy version",
            path="certificate.pc_version",
            details={"cert": cert.pc_version, "validator": policy.version},
        ))

    # Stage 1: ExecutionTrace integrity
    diags.extend(verify_trace_integrity(cert.execution_trace, ctx))

    # Stage 2: Response Contract checks
    diags.extend(check_response_contract(ctx, cert.response))

    # Stage 3: DerivedFacts replay (verification)
    df_outputs, df_diags = replay_derived_facts(ctx, cert.response, cert.execution_trace, cert.derived_facts, ops, )
    diags.extend(df_diags)

    # Stage 4: Policy compliance for referenced clauses
    env = build_env(ctx, cert.response, df_outputs)
    diags.extend(verify_policy_refs_and_compliance(policy, cert.policy_refs.used_clause_ids, env, ))

    # Optional: mandatory baseline policy checks could be enforced here
    # (e.g., always apply public-mode forbids). This stays deterministic.

    # Stage 5: Links grounding
    diags.extend(verify_link_grounding(cert.response, cert.execution_trace, df_outputs))

    # Stage 6: Minimality checks for escape-hatch outcomes
    diags.extend(verify_minimality(cert.response, cert.commitments, policy, env))

    # Stage 7: Write safety (optional placeholder)
    # If you record write calls in trace.req.method != "GET/POST read", you can enforce read-after-write here.

    ok = len(diags) == 0
    return VerificationResult(ok=ok, diagnostics=diags)
