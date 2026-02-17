# ============================================================
# PSEUDO-PYTHON: LLM-driven solve() (produces Response + Certificate)
# ============================================================
from typing import Any, List

Context = Any
Snapshot = Any
ExecutionTrace = Any
DerivedFact = Any
DerivedFacts = Any
PolicyRefs = Any
Commitments = Any
Commitment = Any
Experience = Any
TaskIntent = Any
Plan = Any
Decision = Any
Response = Any
Task = Any


def propose(task: Task, ctx: Context, experience: Experience):
    """
    Returns:
      (1) response
      (2) cert

    Trust boundaries & determinism:
      - This function is executed by the LLM.
      - This function must never "invent" facts; any factual claim should be grounded in:
          * execution_trace responses and/or snapshot tables produced by wrappers
      - DerivedFacts must be expressed via a replayable, deterministic DSL (ops).
      - The external validator (inverse_solve) will deterministically verify:
          * trace integrity
          * derived_facts replay
          * policy clause satisfaction
          * links grounding
          * minimality for escape-hatch outcomes
    """

    # ------------------------------------------------------------
    # 1) Initialize proof containers (always)
    # ------------------------------------------------------------
    policy_refs = []
    commitments = []

    # ------------------------------------------------------------
    # 2) Interpret task (LLM semantic step) -> Structured TaskIntent
    # ------------------------------------------------------------
    intent = interpret(task, experience)

    # ------------------------------------------------------------
    # 3) Plan deterministic data access & operations
    # ------------------------------------------------------------
    plan = build_plan(intent, ctx, experience)
    """
      - Plan chooses which deterministic wrappers to call (or which context tables to use),
        and which DerivedFacts ops to record for replay.
      - Prefer using context tables (prefetch) to avoid extra API calls.
      - If additional API calls are needed, call wrappers that append to execution_trace.
      - Plan should also include "candidate alternatives" for minimality checks:
          plan.alternatives = ["ok_answer", "ok_not_found", "denied_security", ...]
    """

    # ------------------------------------------------------------
    # 4) Execute plan via deterministic wrappers (no raw HTTP)
    # ------------------------------------------------------------
    # The wrapper ensures calls are recorded in et.calls with response hashes and embedded responses.
    tracing, raw_results = execute_plan(plan, ctx)
    """
      - Deterministic wrappers must:
          * perform the actual REST calls
          * record each call into et.calls
          * record discovered entities into et.artifacts
      - raw_results is an ephemeral structure for the LLM; it should be reconstructible from et + snapshot.
    """

    # ------------------------------------------------------------
    # 5) Build DerivedFacts (replayable ops) from trace + snapshot
    # ------------------------------------------------------------
    df = derive_facts(plan, tracing, ctx, intent)
    """
      - DerivedFacts must be an ordered list of nodes that the validator can replay deterministically.
      - Each node uses an allowed op (e.g., json_select, normalize, classify, join_by_id, compute_links_minimal).
      - IMPORTANT: DerivedFacts are not "LLM assertions"; they must be computationally checkable.
      - Examples of nodes:
          * SelectFact: select entity record from a particular API call response via JSON pointer
          * NormalizeFact: normalize strings for matching/reporting
          * ClassifyFact: classify data sensitivity from fields (deterministic heuristic aligned to policy)
          * JoinFact: join lists by id
    """

    # ------------------------------------------------------------
    # 6) Decide outcome and assemble response content
    # ------------------------------------------------------------
    # Always try to produce ok_answer when allowed & supported by grounded data.
    decision = decide_response(intent, ctx, df, tracing, experience)

    response = build_response(decision, df, tracing, ctx)

    # ------------------------------------------------------------
    # 7) Attach PolicyRefs (which clauses are claimed to justify the decision)
    # ------------------------------------------------------------
    policy_refs.used_clause_ids = set(decision.policy_clause_ids)
    """
      - The validator will check referenced clauses exist and are satisfied under Env(ctx, df, response).
      - Do not reference irrelevant clauses; reference only those used for compliance and minimality.
    """

    # ------------------------------------------------------------
    # 8) Build Commitments (proof obligations)
    # ------------------------------------------------------------
    commitments += build_trace_binding_commitments(df, tracing, response)
    commitments += build_link_grounding_commitments(response, tracing, df, ctx)
    commitments += build_policy_compliance_commitments(response, ctx, df, policy_refs)
    commitments += build_noninterference_commitments(response, ctx)
    commitments += build_write_safety_commitments_if_needed(intent, plan, tracing, df, response)

    # Minimality is mandatory for escape-hatch outcomes
    if response.outcome in {"ok_not_found", "denied_security", "none_clarification_needed", "none_unsupported",
                            "error_internal"}:
        commitments += build_minimality_commitment(intent, decision, ctx, df, tracing, response, policy_refs, plan)
    """
      - commitments are structured, validator-checkable statements.
      - Key kinds:
          * trace_binding: every key fact comes from a specific call + selector (or snapshot table)
          * link_grounding: each response link is grounded in et.artifacts and supported by DF nodes
          * policy_compliance: claims of policy adherence (e.g., public redaction, sensitive restrictions)
          * noninterference: asserts no forbidden patterns appear in message (public)
          * write_safety: if writes occurred, attach read-after-write confirmation steps
          * minimality: for escape-hatch outcomes, prove ok_answer was impossible (or not permitted)
    """

    # ------------------------------------------------------------
    # 9) Package plan (final)
    # ------------------------------------------------------------
    return Plan(request=task, execution_trace=tracing, facts=df, policy_refs=policy_refs, commitments=commitments)


# ============================================================
# Sub-functions (pseudo-Python + NL docstrings)
# ============================================================

def determine_mode(ctx: Context) -> str:
    """
    Deterministic:
      - Use ctx.whoami to decide mode, never guess.
      - Return "public" if ctx.is_public else "authenticated".
    """
    return "public" if ctx.is_public else "authenticated"


def interpret(task: Task, experience: Experience) -> TaskIntent:
    """
    - This is a semantic parsing step.
    - Output should be a small structured object, e.g.:
      intent.kind: "lookup_employee" | "list_project_employees" | "log_time" | ...
      intent.entities: {names, identifiers, dates, etc.}
      intent.needs_write: bool
      intent.expected_links: set[LinkKind]
      intent.risk_level: "low"|"medium"|"high"
    - If the task is ambiguous, intent.kind may be "needs_clarification".
    - The validator will NOT verify "intent correctness"; it will verify consistency of proof.

    LLM responsibility (semantic):
    - Extract what the user asks (lookup/list/update/write/report).
    - Identify candidate entity types (employee/project/customer/timelog).
    - Identify missing required parameters; if missing -> "needs_clarification".
    - Identify whether write operations are required.

    Determinism constraints:
    - Provide a compact JSON-like structure.
    - Do not perform API calls here.
    """
    pass


def build_plan(intent: TaskIntent, ctx, experience: Experience) -> Plan:
    """
    LLM responsibility (planning):
      - Choose which snapshot tables to consult and which wrappers to call.
      - Prefer deterministic aggregations: paging joins in wrappers, not trial-and-error.
      - Include minimality alternatives to be checked if escape-hatch is selected.

    Deterministic constraints:
      - Plan is just a description, execution happens in wrappers.
    """
    pass


def execute_plan(plan, ctx) -> ExecutionTrace:
    """
    Wrapper responsibility (deterministic IO):
      - Execute all planned API calls.
      - Append each call with response + response_hash to et.calls.
      - Extract discovered entities and store them in et.artifacts.

    LLM responsibility:
      - Provide the plan.
      - Consume results.

    Return:
      - updated execution_trace
      - raw_results (ephemeral convenience; must be reconstructible from et + snapshot)
    """
    # for step in plan.steps:
    #   if step.kind == "use_snapshot": read from snapshot.tables
    #   if step.kind == "api_call": resp = wrapper.call(step.endpoint, step.params); et.calls.append(...)
    #   if step.kind == "extract_artifacts": et.artifacts.extend(...)
    pass


def derive_facts(plan, et, ctx, intent) -> List[DerivedFact]:
    """
    LLM responsibility (proof construction):
      - Emit a replayable list of DerivedFacts nodes.
      - Each node must be computable deterministically from:
          * et.calls responses (via selectors)
          * snapshot tables
          * ctx fields
      - Must not embed unverifiable statements.

    Validator responsibility:
      - Replay these nodes with allowed ops and compare computed output == declared output.

    Minimal recommended nodes:
      - SelectFact(call_id, json_pointer) -> {"value": ...}
      - NormalizeFact(inputs=[...], op="norm_person_name") -> {"norm_name": ...}
      - ClassifyFact(inputs=[...], op="data_class_from_fields") -> {"data_class": ...}
      - JoinFact(inputs=[list, id], op="join_by_id") -> {"value": ...}
    """
    # Example:
    # df.add(SelectFact(id="f1", call_id="c7", json_pointer="/items/0", output={"value": {...}}))
    # df.add(ClassifyFact(id="f2", inputs=["f1"], output={"data_class": "internal"}))
    pass


def decide_response(intent, ctx, df, et, experience) -> Decision:
    """
    - Decision is an LLM step constrained by policies and grounded facts.
    - It should output:
          decision.outcome
          decision.message_template_id (optional)
          decision.message_args (grounded values only)
          decision.link_targets: list[(kind,id)] (must be in et.artifacts)
          decision.policy_clause_ids: list[str]  (used as policy_refs)
    - The message must not contain disallowed content (especially in public mode).
    - For write tasks, decision must include required fields (e.g., JIRA ticket) or choose clarification/deny.

    LLM responsibility (decision under constraints):
      - Choose an outcome and message plan consistent with policies and available grounded facts.
      - Prefer ok_answer if:
          * required data is available and
          * policies permit disclosure and
          * links can be grounded
      - Otherwise choose minimal escape-hatch outcome:
          * ok_not_found: proved not found
          * denied_security: proved forbidden
          * none_clarification_needed: proved missing input not derivable
          * none_unsupported: proved task outside capability/endpoints
          * error_internal: only for genuine internal failures

    Deterministic constraints:
      - Output decision is structured.
      - Policy clause IDs referenced must exist in compiled policy.
    """
    pass


def build_response(decision, df, et, ctx) -> Response:
    """
    - response.message must be built from grounded values (trace/snapshot), not invented.
    - response.links must correspond to et.artifacts and must be policy-compliant.
    - outcome-specific contracts must be honored:
          * denied_security -> links must be empty
          * ok_not_found    -> links must be empty
          * clarification   -> ask for missing parameter(s)

    LLM responsibility (text generation within guardrails):
      - Compose message using grounded values only.
      - Ensure public mode redaction (no internal IDs, no PII patterns).
      - Ensure outcome contracts are satisfied (e.g., links empty for denied_security).

    Deterministic constraints:
      - links must be a subset of et.artifacts unless outcome requires empty links.
    """
    # pseudo:
    # message = render_template(decision.template_id, decision.args)
    # links = build_links(decision.link_targets, et, decision.outcome)
    pass


# ============================================================
# Commitments builders (LLM must provide checkable structure)
# ============================================================

def build_trace_binding_commitments(df, et, response):
    """
    Purpose:
      - For each critical fact used in response/links, bind it to:
          * a specific et.calls call_id and selector
          * or a snapshot table row + key
      - This supports "no hallucination": every fact is trace-grounded.

    Validator:
      - Verifies that referenced call_id exists, selector is valid, and output matches.
    """
    return [Commitment(kind="trace_binding", claims=[...])]


def build_link_grounding_commitments(response, et, df, ctx):
    """
    Purpose:
      - Prove each (kind,id) in response.links exists in et.artifacts.
      - Prove it is relevant to the message (optional but recommended).
      - Enforce outcome constraints: links empty for denied_security/ok_not_found.

    Validator:
      - Checks membership in et.artifacts + policy restrictions.
    """
    return [Commitment(kind="link_grounding", claims=[...])]


def build_policy_compliance_commitments(response, ctx, df, policy_refs):
    """
    Purpose:
      - Prove compliance with key policies:
          * public redaction constraints
          * data classification restrictions (sensitive/highly)
          * write prerequisites (e.g., required fields)
      - Reference the specific policy clause IDs that justify the decision.

    Validator:
      - Evaluates referenced clauses under env(ctx, df, response) deterministically.
    """
    return [Commitment(kind="policy_compliance", claims=[...])]


def build_noninterference_commitments(response, ctx):
    """
    Purpose:
      - Assert that response message does not contain forbidden patterns.
      - Especially important in public mode.

    Validator:
      - Runs deterministic regex checks.
    """
    return [Commitment(kind="noninterference", claims=[...])]


def build_write_safety_commitments_if_needed(intent, plan, et, df, response):
    """
    Purpose:
      - If plan includes writes:
          * prove write is authorized by policy clauses
          * prove required fields present
          * prove read-after-write postcondition checks exist in execution_trace

    Validator:
      - Checks ET includes write call(s) and required postcondition calls.
    """
    if not intent.needs_write:
        return []
    return [Commitment(kind="write_safety", claims=[...])]


def build_minimality_commitment(intent, decision, ctx, df, et, response, policy_refs, plan):
    """
    Purpose:
      - Prevent 'deny-bot' behavior by proving escape-hatch outcome is necessary.

    Minimal deterministic structure:
      - for_outcome: response.outcome
      - checked_alternatives:
          * ok_answer must be marked impossible with a reason_clause_id
      - The reason_clause_id must be a real policy clause applicable under env.

    Validator:
      - Ensures at least ok_answer is considered and marked impossible.
      - Ensures reason clause exists and is applicable.
    """
    return [Commitment(kind="minimality", for_outcome=response.outcome, checked_alternatives=[...])]
