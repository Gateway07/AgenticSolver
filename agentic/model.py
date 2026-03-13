from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, HttpUrl


# ============================================================================
# Functional-OOP relations
# ----------------------------------------------------------------------------
# map:
# - DraftSourceInventory -> SourceInventory
# - DraftDomainMemory -> DomainMemory
# - DomainMemory -> DomainMemorySlice
# - DraftTaskFrame -> TaskFrame
# - DraftRunDistill -> RunDistill
# - DraftDesignIR -> DesignIR
# - list[SearchHintIR] + TaskFrame -> DeterministicSearchHints
#
# instanceOf:
# - FlowPlan -> RunTrace
# - list[SearchHintIR] -> DeterministicSearchHints
#
# include:
# - DomainMemory -> aliases, rules, task patterns, endpoint specs, ontology, and failures
# - DomainMemorySlice -> a subset of DomainMemory
# - DesignIR -> SchemaIR / PolicyIR / QueryIR / PrimitiveIR / TemplateIR
# - CompiledArtifacts -> models_py / primitives_py / views_sql / policies_rego / templates_py
# - PrimitiveRegistry -> PrimitiveIR items
# - GrammarProfileRegistry -> GrammarProfile items
#
# Feedback signals:
# - RunTrace
# - RunDistill
# - FailureCatalog
# - AbstractionCorpus
# - DesignVerificationReport
# - list[CoverageCase]
# - list[RegressionCase]
# - LibraryCompressionDelta
# ============================================================================


class PageSnapshot(BaseModel):
    """Raw benchmark entry page fetched from the initial URL before semantic interpretation."""
    url: HttpUrl = Field(..., description="The entry URL used to bootstrap the system.")
    blocks: list[str] = Field(..., description="Text paragraphs or blocks extracted from the HTML page.")
    links: list[str] = Field(..., description="Raw links extracted from the HTML page as strings.")


class SourceDocument(BaseModel):
    """A fetched source document with raw content and provenance metadata."""
    url: HttpUrl = Field(..., description="The canonical URL of the fetched document.")
    kind: Literal["raw_wiki", "endpoint_doc", "task_ref", "other"] = Field(
        ..., description="The semantically classified kind of the source document."
    )
    content: str = Field(..., description="The raw document content.")


class DraftSourceInventory(BaseModel):
    """Draft semantic classification of source candidates discovered on the entry page."""
    raw_candidates: list[str] = Field(...,
                                      description="Candidate links or textual references that may point to raw static sources.")
    endpoint_candidates: list[str] = Field(...,
                                           description="Candidate links or textual references that may point to endpoint documentation.")
    task_ref_candidates: list[str] = Field(...,
                                           description="Candidate links or textual references that may point to hidden task sources.")
    notes: list[str] = Field(..., description="Free-form draft observations produced during semantic source discovery.")


class SourceInventory(BaseModel):
    """Canonical discovered source groups derived from the raw entry page."""
    raw_urls: list[HttpUrl] = Field(..., description="Validated canonical URLs that point to raw wiki sources.")
    endpoint_urls: list[HttpUrl] = Field(...,
                                         description="Validated canonical URLs that point to endpoint documentation.")
    task_ref_urls: list[HttpUrl] = Field(...,
                                         description="Validated canonical URLs that point to task references or task loaders.")


class Violation(BaseModel):
    """A deterministic validation or verification issue."""
    code: str = Field(..., description="A stable machine-readable issue code.")
    severity: Literal["info", "warning", "error"] = Field(..., description="The severity level of the issue.")
    message: str = Field(..., description="A human-readable issue explanation.")
    location: str = Field(..., description="The logical location where the issue was detected.")


class SchemaValidationSpec(BaseModel):
    """Structural validation rules for typed artifacts."""
    artifact_name: str = Field(..., description="The logical artifact name used for diagnostics.")
    required_fields: list[str] = Field(..., description="Field names that must be present.")
    allow_extra_fields: bool = Field(..., description="Whether unknown fields are allowed.")
    allowed_enum_values: dict[str, list[str]] = Field(..., description="Allowed enum-like values per field path.")
    regex_constraints: dict[str, str] = Field(..., description="Regular expression constraints per field path.")
    min_items: dict[str, int] = Field(..., description="Minimum list lengths per field path.")
    max_items: dict[str, int] = Field(..., description="Maximum list lengths per field path.")
    cross_field_rules: list[str] = Field(..., description="Declarative structural invariants spanning multiple fields.")


class SchemaValidationReport(BaseModel):
    """Result of structural validation."""
    passed: bool = Field(..., description="Whether structural validation passed.")
    issues: list[Violation] = Field(..., description="Collected structural validation issues.")


class RegistryStorageStatus(BaseModel):
    """Result of persisting active registry state."""
    stored: bool = Field(..., description="Whether the snapshot was stored successfully.")
    version_id: str = Field(..., description="The assigned version identifier for the stored snapshot.")
    issues: list[Violation] = Field(..., description="Storage-related issues or warnings.")


class EntityTerm(BaseModel):
    """A canonical domain entity term."""
    entity_type: str = Field(..., description="The entity type, such as project or employee.")
    canonical_name: str = Field(..., description="The canonical entity name.")
    description: str = Field(..., description="A concise semantic description of the entity term.")


class RuleClause(BaseModel):
    """A normalized domain rule with traceability."""
    id: str = Field(..., description="A stable identifier for the rule.")
    natural_text: str = Field(..., description="The original or near-original natural language rule text.")
    normalized_form: str = Field(..., description="A normalized formal or semi-formal rule representation.")
    source_url: str = Field(description="The source URL for the rule or an empty string if unavailable.")


class TaskPattern(BaseModel):
    """A recurring task family pattern."""
    id: str = Field(..., description="A stable identifier for the task pattern.")
    intent_family: str = Field(..., description="The coarse-grained intent family associated with the pattern.")
    trigger_phrases: list[str] = Field(..., description="Lexical triggers associated with the pattern.")
    notes: str = Field(..., description="Concise notes about when and how the pattern applies.")


class AliasMaps(BaseModel):
    """Canonical alias mappings used by deterministic normalizers."""
    entity_aliases: dict[str, str] = Field(..., description="Mappings from entity aliases to canonical identifiers.")
    endpoint_aliases: dict[str, str] = Field(..., description="Mappings from endpoint aliases to canonical families.")
    intent_aliases: dict[str, str] = Field(..., description="Mappings from intent aliases to canonical labels.")
    policy_aliases: dict[str, str] = Field(..., description="Mappings from policy aliases to canonical cues.")


class EndpointSpec(BaseModel):
    """A canonical endpoint contract record."""
    family: str = Field(..., description="The endpoint family identifier.")
    method: Literal["GET", "POST", "PUT", "PATCH", "DELETE"] = Field(...,
                                                                     description="The HTTP method used by the endpoint.")
    path: str = Field(..., description="The HTTP path template of the endpoint.")
    request_shape: str = Field(..., description="A concise request payload contract description.")
    response_shape: str = Field(..., description="A concise response payload contract description.")
    mutable: bool = Field(..., description="Whether the endpoint changes persistent state.")


class FailureRecord(BaseModel):
    """A normalized known failure pattern."""
    id: str = Field(..., description="A stable identifier for the failure pattern.")
    symptom: str = Field(..., description="The observable symptom of the failure.")
    likely_cause: str = Field(..., description="The most likely cause associated with the symptom.")
    detector_hint: str = Field(..., description="A concise hint for detecting this failure.")
    run_refs: list[str] = Field(..., description="Run identifiers linked to this failure pattern.")


class RuntimeOntology(BaseModel):
    """Allowed runtime labels and structural constraints."""
    allowed_intents: list[str] = Field(..., description="Canonical runtime intent labels.")
    allowed_policy_cues: list[str] = Field(..., description="Canonical policy cue labels.")
    allowed_endpoint_families: list[str] = Field(..., description="Canonical endpoint family identifiers.")
    allowed_profiles: list[str] = Field(..., description="Canonical runtime profile identifiers.")


class DraftDomainMemory(BaseModel):
    """Draft semantic memory produced by the LLM."""
    entity_terms: list[EntityTerm] = Field(..., description="Draft canonical entity terms.")
    rules: list[RuleClause] = Field(..., description="Draft normalized rule clauses.")
    aliases: AliasMaps = Field(..., description="Draft alias mappings.")
    task_patterns: list[TaskPattern] = Field(..., description="Draft recurring task patterns.")
    notes: list[str] = Field(..., description="Free-form draft notes produced during distillation.")


class DomainMemory(BaseModel):
    """Canonical domain memory used by design-time and runtime."""
    entity_terms: list[EntityTerm] = Field(..., description="Canonical domain entity terms.")
    rules: list[RuleClause] = Field(..., description="Canonical normalized rules.")
    aliases: AliasMaps = Field(..., description="Canonical alias mappings.")
    task_patterns: list[TaskPattern] = Field(..., description="Canonical task patterns.")
    endpoint_specs: list[EndpointSpec] = Field(..., description="Canonical endpoint specifications.")
    ontology: RuntimeOntology = Field(..., description="Canonical runtime ontology.")
    failure_catalog: list[FailureRecord] = Field(..., description="Canonical accumulated failure catalog.")


class IntentGuess(BaseModel):
    """A typed intent guess extracted from task text."""
    label: str = Field(..., description="The canonical or near-canonical intent label.")
    confidence: float = Field(..., description="The confidence assigned to the intent guess.")
    evidence_spans: list[str] = Field(..., description="Text spans that support the intent guess.")


class EntityMention(BaseModel):
    """A detected entity mention and its canonical binding if available."""
    entity_type: str = Field(..., description="The entity type, such as project or employee.")
    surface: str = Field(..., description="The raw surface text of the entity mention.")
    canonical_id: str = Field(..., description="The resolved canonical identifier or an empty string.")
    confidence: float = Field(..., description="The confidence assigned to the entity binding.")


class PolicyCue(BaseModel):
    """A detected policy-related cue."""
    label: str = Field(..., description="The canonical or near-canonical policy cue label.")
    surface: str = Field(..., description="The raw text span that triggered the cue.")
    confidence: float = Field(..., description="The confidence assigned to the cue.")


class EndpointCue(BaseModel):
    """A predicted endpoint family cue used for runtime narrowing."""
    family: str = Field(..., description="The canonical or near-canonical endpoint family.")
    confidence: float = Field(..., description="The confidence assigned to the cue.")


class DraftTaskFrame(BaseModel):
    """Draft task grounding produced by the LLM."""
    intent: IntentGuess = Field(..., description="Draft task intent.")
    entities: list[EntityMention] = Field(..., description="Draft entity mentions.")
    policy_cues: list[PolicyCue] = Field(..., description="Draft policy cues.")
    endpoint_cues: list[EndpointCue] = Field(..., description="Draft endpoint cues.")
    recommended_profile: str = Field(..., description="Draft recommended runtime profile.")


class TaskFrame(BaseModel):
    """Canonical runtime control frame used by deterministic flow planning."""
    intent: IntentGuess = Field(..., description="Canonical runtime intent.")
    entities: list[EntityMention] = Field(..., description="Canonical entity mentions.")
    policy_cues: list[PolicyCue] = Field(..., description="Canonical policy cues.")
    endpoint_cues: list[EndpointCue] = Field(..., description="Canonical endpoint cues.")
    recommended_profile: str = Field(..., description="Canonical runtime profile.")
    warnings: list[str] = Field(..., description="Normalization warnings or safety downgrades.")


class SearchHintIR(BaseModel):
    """A design-time search hint rule that can later guide runtime planning."""
    id: str = Field(..., description="A stable identifier for the search hint.")
    intent_match: list[str] = Field(..., description="Intent labels that activate this hint.")
    profile_match: list[str] = Field(..., description="Profile labels that activate this hint.")
    ranked_primitive_families: list[str] = Field(..., description="Primitive families ranked by preference.")
    repair_order: list[str] = Field(..., description="Repair actions ranked by preference.")


class DeterministicSearchHints(BaseModel):
    """Concrete per-task runtime hints resolved from active hint rules."""
    ranked_primitive_families: list[str] = Field(..., description="Primitive families ranked for the current task.")
    repair_order: list[str] = Field(..., description="Repair actions ranked for the current task.")
    excluded_families: list[str] = Field(..., description="Primitive families excluded for the current task.")


class GrammarProfile(BaseModel):
    """A runtime grammar profile constraining flow assembly."""
    id: str = Field(..., description="The stable profile identifier.")
    allowed_primitive_families: list[str] = Field(..., description="Primitive families allowed under this profile.")
    fallback_profile_id: str = Field(..., description="The fallback profile identifier or an empty string.")


class GrammarProfileRegistry(BaseModel):
    """The active set of runtime grammar profiles."""
    items: list[GrammarProfile] = Field(..., description="Active runtime grammar profiles.")


class PrimitiveIR(BaseModel):
    """A canonical primitive contract and binding descriptor."""
    id: str = Field(..., description="The stable primitive identifier.")
    family: str = Field(..., description="The primitive family identifier.")
    inputs: list[str] = Field(..., description="Declared input contracts.")
    outputs: list[str] = Field(..., description="Declared output contracts.")
    preconditions: list[str] = Field(..., description="Required preconditions.")
    postconditions: list[str] = Field(..., description="Guaranteed postconditions.")
    binding_name: str = Field(..., description="The deterministic binding name used by the executor.")


class PrimitiveCandidateIR(BaseModel):
    """A candidate primitive proposed before final promotion."""
    id: str = Field(..., description="The proposed primitive identifier.")
    family: str = Field(..., description="The proposed primitive family.")
    inputs: list[str] = Field(..., description="Proposed input contracts.")
    outputs: list[str] = Field(..., description="Proposed output contracts.")
    preconditions: list[str] = Field(..., description="Proposed preconditions.")
    postconditions: list[str] = Field(..., description="Proposed postconditions.")
    evidence_refs: list[str] = Field(..., description="Evidence references supporting the proposal.")


class PrimitiveRegistry(BaseModel):
    """The active registry of live runtime primitives."""
    items: list[PrimitiveIR] = Field(..., description="Active runtime primitive contracts.")


class TemplateIR(BaseModel):
    """A reusable structural template for design-time or runtime assembly."""
    id: str = Field(..., description="The stable template identifier.")
    description: str = Field(..., description="A concise explanation of the template.")
    parameter_slots: list[str] = Field(..., description="Named parameter slots used by the template.")
    applicability_conditions: list[str] = Field(..., description="Conditions under which the template may be applied.")


class SchemaFieldIR(BaseModel):
    """A field specification inside a generated schema."""
    name: str = Field(..., description="The field name.")
    field_type: str = Field(..., description="The declared field type.")
    required: bool = Field(..., description="Whether the field is mandatory.")


class SchemaIR(BaseModel):
    """A canonical schema specification intended for code generation."""
    id: str = Field(..., description="The stable schema identifier.")
    fields: list[SchemaFieldIR] = Field(..., description="The schema field specifications.")


class PolicyIR(BaseModel):
    """A canonical policy specification intended for Rego generation."""
    id: str = Field(..., description="The stable policy identifier.")
    rules: list[str] = Field(..., description="Normalized policy rules.")


class QueryIR(BaseModel):
    """A canonical query or view specification intended for SQL generation."""
    id: str = Field(..., description="The stable query identifier.")
    source_tables: list[str] = Field(..., description="Source tables referenced by the query.")
    filters: list[str] = Field(..., description="Filter predicates applied by the query.")
    group_by: list[str] = Field(..., description="Grouping keys used by the query.")
    aggregates: list[str] = Field(..., description="Aggregate expressions used by the query.")


class DraftDesignIR(BaseModel):
    """Draft design-time IR produced by the LLM."""
    schemas: list[SchemaIR] = Field(..., description="Draft schema IR blocks.")
    policies: list[PolicyIR] = Field(..., description="Draft policy IR blocks.")
    queries: list[QueryIR] = Field(..., description="Draft query IR blocks.")
    primitives: list[PrimitiveIR] = Field(..., description="Draft primitive IR blocks.")
    templates: list[TemplateIR] = Field(..., description="Draft reusable templates.")


class DesignIR(BaseModel):
    """Canonical design-time IR ready for deterministic compilation."""
    schemas: list[SchemaIR] = Field(..., description="Canonical schema IR blocks.")
    policies: list[PolicyIR] = Field(..., description="Canonical policy IR blocks.")
    queries: list[QueryIR] = Field(..., description="Canonical query IR blocks.")
    primitives: list[PrimitiveIR] = Field(..., description="Canonical primitive IR blocks.")
    templates: list[TemplateIR] = Field(..., description="Canonical reusable templates.")


class CompiledArtifacts(BaseModel):
    """Generated code bundle produced from canonical design-time IR."""
    models_py: str = Field(..., description="Generated Python model code.")
    primitives_py: str = Field(..., description="Generated Python primitive binding code.")
    views_sql: str = Field(..., description="Generated SQL code for views and queries.")
    policies_rego: str = Field(..., description="Generated Rego policy code.")
    templates_py: str = Field(..., description="Generated Python helper code for reusable templates.")


class FlowNode(BaseModel):
    """A single replayable node inside a runtime flow plan."""
    id: str = Field(..., description="The stable node identifier inside the flow.")
    primitive_id: str = Field(..., description="The primitive executed by this node.")
    args: dict[str, str] = Field(..., description="The node arguments expressed as key-value pairs.")
    depends_on: list[str] = Field(..., description="Node identifiers that must finish before this node.")


class FlowPlan(BaseModel):
    """A deterministic runtime plan built from allowed primitives."""
    id: str = Field(..., description="The stable plan identifier.")
    profile_id: str = Field(..., description="The runtime grammar profile applied to the plan.")
    nodes: list[FlowNode] = Field(..., description="Replayable runtime nodes.")
    success_criteria: list[str] = Field(..., description="Conditions that define plan success.")
    stop_conditions: list[str] = Field(..., description="Conditions that terminate execution early.")


class TraceEvent(BaseModel):
    """A single execution event recorded during runtime."""
    id: str = Field(..., description="The runtime node that produced this event.")
    primitive_id: str = Field(..., description="The primitive executed by the node.")
    status: Literal["ok", "fail", "blocked"] = Field(..., description="The execution outcome of the node.")
    input_refs: list[str] = Field(..., description="References to inputs consumed by the node.")
    output_ref: str = Field(..., description="Reference to the produced output or an empty string.")
    violations: list[str] = Field(..., description="Policy or contract violations emitted by the node.")
    cost_ms: int = Field(..., description="Execution cost in milliseconds.")


class RunTrace(BaseModel):
    """Immutable runtime evidence for one executed flow plan."""
    id: str = Field(..., description="The stable run identifier.")
    plan_id: str = Field(..., description="The executed flow plan identifier.")
    events: list[TraceEvent] = Field(..., description="Recorded execution events.")
    success: bool = Field(..., description="Whether the run completed successfully.")
    final_score: float = Field(..., description="The final benchmark or task score for the run.")


class DraftRunDistill(BaseModel):
    """Draft post-run learning summary produced by the LLM."""
    lessons: list[str] = Field(..., description="Draft reusable lessons extracted from the run.")
    failure_refs: list[str] = Field(..., description="Draft failure identifiers referenced by the summary.")
    hypothesis_notes: list[str] = Field(..., description="Draft hypotheses or explanations produced after the run.")


class RunDistill(BaseModel):
    """Canonical and validated post-run learning signal."""
    lessons: list[str] = Field(..., description="Validated reusable lessons extracted from the run.")
    failure_refs: list[str] = Field(..., description="Validated failure identifiers linked to the run.")
    hypothesis_notes: list[str] = Field(..., description="Validated hypotheses retained for future learning.")
    grounded_run_id: str = Field(..., description="The run identifier that grounds this distillation.")


class AbstractionCorpus(BaseModel):
    """Structured design-time corpus built from traces, plans, and grounded task frames."""
    fragment_signatures: list[str] = Field(..., description="Canonical signatures of extracted reusable fragments.")
    usage_counts: dict[str, int] = Field(..., description="Usage frequencies keyed by fragment signature.")
    evidence_refs: list[str] = Field(..., description="References to traces, plans, or tasks supporting the corpus.")


class DraftAbstractionSet(BaseModel):
    """Draft abstraction proposals produced by the LLM."""
    primitive_candidates: list[PrimitiveCandidateIR] = Field(...,
                                                             description="Draft primitive candidates proposed from the corpus.")
    search_hints: list[SearchHintIR] = Field(..., description="Draft runtime search hints proposed from the corpus.")
    templates: list[TemplateIR] = Field(..., description="Draft reusable templates proposed from the corpus.")


class LibraryCompressionDelta(BaseModel):
    """A deterministic change-set describing extract, merge, and prune actions."""
    extract_ids: list[str] = Field(..., description="Identifiers to extract as reusable abstractions.")
    merge_pairs: list[tuple[str, str]] = Field(..., description="Pairs of identifiers that should be merged.")
    prune_ids: list[str] = Field(..., description="Identifiers that should be removed from active use.")
    estimated_gain: float = Field(..., description="Estimated compression or simplification gain.")


class CoverageCase(BaseModel):
    """A generated coverage-oriented verification case."""
    id: str = Field(..., description="The stable coverage case identifier.")
    description: str = Field(..., description="A concise explanation of the coverage target.")


class RegressionCase(BaseModel):
    """A frozen regression case that must continue to pass."""
    id: str = Field(..., description="The stable regression case identifier.")
    description: str = Field(..., description="A concise explanation of the regression guarantee.")


class DesignVerificationReport(BaseModel):
    """Formal verification result used for promotion decisions."""
    passed: bool = Field(..., description="Whether the full verification pass succeeded.")
    static_checks_passed: bool = Field(..., description="Whether static and structural checks passed.")
    coverage_cases_passed: int = Field(..., description="The number of passed coverage cases.")
    regression_cases_passed: int = Field(..., description="The number of passed regression cases.")
    issues: list[Violation] = Field(..., description="Collected verification issues.")
