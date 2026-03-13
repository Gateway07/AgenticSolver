# ----------------------------------------------------------------------------
# Meta-interpreter specs
# ----------------------------------------------------------------------------

from model import *


class RegistryStorageSpec(BaseModel):
    """Persistence policy for registry snapshots."""
    namespace: str = Field(..., description="The storage namespace for registry snapshots.")
    versioning_enabled: bool = Field(..., description="Whether versioning must be applied.")
    keep_history: bool = Field(..., description="Whether historical snapshots must be retained.")


class CompilationTemplateSpec(BaseModel):
    """Deterministic code generation policy."""
    target_python_version: str = Field(..., description="The target Python version for generated Python code.")
    emit_pydantic_models: bool = Field(..., description="Whether model code should be emitted.")
    emit_sql_views: bool = Field(..., description="Whether SQL view code should be emitted.")
    emit_rego_policies: bool = Field(..., description="Whether Rego policy code should be emitted.")
    emit_python_templates: bool = Field(..., description="Whether template helper Python code should be emitted.")


class VerificationSpec(BaseModel):
    """Generic verification policy interpreted by the verifier engine."""
    fail_on_warning: bool = Field(..., description="Whether warnings should fail verification.")
    require_static_checks: bool = Field(..., description="Whether structural and parse checks are mandatory.")
    require_coverage: bool = Field(..., description="Whether generated coverage cases are mandatory.")
    require_regressions: bool = Field(..., description="Whether regression cases are mandatory.")


class ExecutionSpec(BaseModel):
    """Generic runtime execution policy."""
    stop_on_first_failure: bool = Field(..., description="Whether execution stops on the first failed step.")
    record_all_events: bool = Field(..., description="Whether every execution event must be persisted.")
    enforce_policy_checks: bool = Field(..., description="Whether policy checks are enforced during execution.")


class PromotionSpec(BaseModel):
    """Policy controlling promotion of verified design artifacts."""
    require_full_pass: bool = Field(..., description="Whether only fully passing reports may be promoted.")
    create_version_snapshot: bool = Field(..., description="Whether a new version snapshot must be created.")
    update_registries_atomically: bool = Field(
        ..., description="Whether active registries must be updated atomically."
    )


class MemoryNormalizationSpec(BaseModel):
    """Normalization policy for draft domain memory."""
    deduplicate_rules: bool = Field(..., description="Whether semantically duplicate rules must be merged.")
    canonicalize_aliases: bool = Field(..., description="Whether aliases must be normalized into canonical maps.")
    build_runtime_ontology: bool = Field(...,
                                         description="Whether runtime ontology must be derived during normalization.")


class SourceInventoryNormalizationSpec(BaseModel):
    """Normalization policy for draft source discovery."""
    require_absolute_urls: bool = Field(..., description="Whether all discovered source URLs must be absolute.")
    allow_duplicate_candidates: bool = Field(..., description="Whether duplicate candidate URLs are tolerated.")
    allow_unknown_source_groups: bool = Field(
        ..., description="Whether unmatched candidates may be ignored without failing normalization."
    )


class MemorySliceSpec(BaseModel):
    """Selection policy for building a focused domain memory slice."""
    max_rules: int = Field(..., description="Maximum number of rules to include in one slice.")
    max_patterns: int = Field(..., description="Maximum number of task patterns to include in one slice.")
    include_endpoint_specs: bool = Field(
        ..., description="Whether endpoint specifications must be included in the slice."
    )


class AbstractionNormalizationSpec(BaseModel):
    """Normalization policy for draft abstraction proposals."""
    allow_new_families: bool = Field(..., description="Whether new primitive families may be accepted.")
    require_contracts: bool = Field(..., description="Whether inputs and outputs are mandatory for candidates.")
    canonicalize_names: bool = Field(..., description="Whether candidate names must be normalized.")


class DesignNormalizationSpec(BaseModel):
    """Normalization policy for draft design-time IR."""
    require_cross_reference_consistency: bool = Field(
        ..., description="Whether all references between IR blocks must be consistent."
    )
    reject_unknown_entities: bool = Field(..., description="Whether unknown entity references must be rejected.")
    reject_unknown_endpoints: bool = Field(..., description="Whether unknown endpoint references must be rejected.")


class GroundingNormalizationSpec(BaseModel):
    """Normalization policy for draft task grounding."""
    drop_low_confidence_cues_below: float = Field(
        ..., description="Confidence threshold below which cues must be dropped."
    )
    force_safe_fallback_on_unknown_intent: bool = Field(
        ..., description="Whether unknown intent must trigger the safest runtime profile."
    )
    expand_mandatory_constraints: bool = Field(
        ..., description="Whether hidden mandatory constraints must be added during normalization."
    )


class FlowPlanningSpec(BaseModel):
    """Deterministic runtime planning policy."""
    max_nodes: int = Field(..., description="Maximum number of nodes allowed in one runtime flow.")
    require_explicit_success_criteria: bool = Field(
        ..., description="Whether a plan must contain explicit success criteria."
    )
    allow_profile_downgrade: bool = Field(
        ..., description="Whether profile downgrade is allowed when planning fails under a stricter profile."
    )


class RunDistillNormalizationSpec(BaseModel):
    """Normalization policy for draft post-run distillation."""
    require_trace_grounding: bool = Field(
        ..., description="Whether every distilled claim must be trace-grounded."
    )
    reject_unknown_failure_refs: bool = Field(
        ..., description="Whether unknown failure identifiers must be rejected."
    )


class CorpusBuildSpec(BaseModel):
    """Extraction policy for building the abstraction corpus."""
    include_failed_runs: bool = Field(..., description="Whether failed runs must be included in the corpus.")
    include_repair_fragments: bool = Field(
        ..., description="Whether repair-related fragments must be extracted."
    )
    count_usage_statistics: bool = Field(
        ..., description="Whether usage metrics must be computed during corpus building."
    )
