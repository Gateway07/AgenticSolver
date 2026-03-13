from __future__ import annotations

from abc import ABC, abstractmethod

from spec import *


# ============================================================================
# Class 1: Ready-made general-purpose tools
# ============================================================================

class KernelTool:
    """Trusted low-level tools that exist before any domain-specific knowledge is discovered."""

    def collect_initial_page(self, init_url: HttpUrl) -> PageSnapshot:
        """Fetch the raw benchmark entry page and return a raw snapshot without semantic interpretation."""
        ...

    def fetch_documents(self, urls: list[HttpUrl]) -> list[SourceDocument]:
        """Fetch concrete documents from validated URLs and attach provenance metadata."""
        ...

    def validate_schema(self, artifact: BaseModel, spec: SchemaValidationSpec) -> SchemaValidationReport:
        """Run deterministic structural validation including types, enums, formats, and cross-field constraints."""
        ...

    def compile_templates(self, design_ir: DesignIR, spec: CompilationTemplateSpec) -> CompiledArtifacts:
        """Compile canonical design-time IR into Python, SQL, and Rego code using deterministic templates."""
        ...

    def persist_registries(
            self,
            primitive_registry: PrimitiveRegistry,
            search_hints: list[SearchHintIR],
            grammar_profiles: GrammarProfileRegistry,
            spec: RegistryStorageSpec,
    ) -> RegistryStorageStatus:
        """Persist the active registry state with deterministic versioning and provenance tracking."""
        ...


class MetaInterpreter:
    """Trusted generic engines that interpret policies and specs rather than domain-specific business logic."""

    def verify_design(
            self,
            compiled_artifacts: CompiledArtifacts,
            coverage_cases: list[CoverageCase],
            regressions: list[RegressionCase],
            spec: VerificationSpec,
    ) -> DesignVerificationReport:
        """Run deterministic static, coverage, and regression verification over compiled design artifacts."""
        ...

    def execute_flow(self, flow_plan: FlowPlan, spec: ExecutionSpec) -> RunTrace:
        """Execute a runtime flow deterministically under a fixed execution policy."""
        ...

    def promote_design(
            self,
            report: DesignVerificationReport,
            compiled_artifacts: CompiledArtifacts,
            current_primitive_registry: PrimitiveRegistry,
            current_search_hints: list[SearchHintIR],
            current_grammar_profiles: GrammarProfileRegistry,
            spec: PromotionSpec,
    ) -> tuple[PrimitiveRegistry, list[SearchHintIR], GrammarProfileRegistry]:
        """Assemble the next active registry state from verified artifacts and the current active state."""
        ...


# ============================================================================
# Class 2: Abstract placeholders (generic engines + generated specs)
# ============================================================================

# ---------- A: memory ----------

class DomainMemoryService(ABC):
    """Abstract domain-memory service. Domain-specific behavior is supplied through typed specs and artifacts."""

    @abstractmethod
    def normalize_source_inventory(self, draft_source_inventory: DraftSourceInventory,
                                   spec: SourceInventoryNormalizationSpec) -> SourceInventory:
        """Map draft source discovery into a canonical source inventory with validated URL groups."""
        ...

    @abstractmethod
    def normalize_domain_memory(self, draft_memory: DraftDomainMemory, spec: MemoryNormalizationSpec) -> DomainMemory:
        """Map draft domain memory into canonical domain memory using deterministic normalization rules."""
        ...

    @abstractmethod
    def slice_domain_memory(self, task_text: str, domain_memory: DomainMemory, spec: MemorySliceSpec) -> DomainMemory:
        """Map full domain memory into a focused subset relevant to one task or one synthesis pass."""
        ...


# ---------- B: design-time ----------

class DesignTimeService(ABC):
    """Abstract design-time service. It organizes evidence and normalizes draft design artifacts."""

    @abstractmethod
    def build_abstraction_corpus(
            self,
            traces: list[RunTrace],
            flows: list[FlowPlan],
            task_frames: list[TaskFrame],
            spec: CorpusBuildSpec,
    ) -> AbstractionCorpus:
        """Build a structured abstraction corpus from runtime traces, flow plans, and grounded task frames."""
        ...

    @abstractmethod
    def normalize_abstractions(
            self,
            draft_abstractions: DraftAbstractionSet,
            spec: AbstractionNormalizationSpec,
    ) -> tuple[list[PrimitiveCandidateIR], list[SearchHintIR], list[TemplateIR]]:
        """Map draft abstraction proposals into canonical design-time candidates."""
        ...

    @abstractmethod
    def normalize_design_ir(
            self,
            draft_design_ir: DraftDesignIR,
            spec: DesignNormalizationSpec,
    ) -> DesignIR:
        """Map draft design-time IR into canonical design-time IR before deterministic compilation."""
        ...

    @abstractmethod
    def generate_coverage_cases(
            self,
            design_ir: DesignIR,
            primitive_registry: PrimitiveRegistry,
            grammar_profiles: GrammarProfileRegistry,
    ) -> list[CoverageCase]:
        """Generate deterministic coverage cases from canonical design artifacts and active registries."""
        ...

    @abstractmethod
    def update_regression_cases(
            self,
            existing_regressions: list[RegressionCase],
            verified_runs: list[RunTrace],
    ) -> list[RegressionCase]:
        """Update the frozen regression set using verified historical runs and existing regression guarantees."""
        ...


# ---------- C: runtime ----------

class RunTimeService(ABC):
    """Abstract runtime service. It turns canonical artifacts into deterministic runtime planning and validated learning signals."""

    @abstractmethod
    def normalize_task_frame(
            self,
            draft_grounded_task_frame: DraftTaskFrame,
            spec: GroundingNormalizationSpec,
            ontology: RuntimeOntology,
            aliases: AliasMaps,
    ) -> TaskFrame:
        """Map draft task grounding into a canonical runtime control frame with safety-oriented normalization."""
        ...

    @abstractmethod
    def resolve_search_hints(
            self,
            grounded_task_frame: TaskFrame,
            search_hints: list[SearchHintIR],
    ) -> DeterministicSearchHints:
        """Resolve concrete deterministic search hints for one task from active design-time hint rules."""
        ...

    @abstractmethod
    def plan_flow(
            self,
            grounded_task_frame: TaskFrame,
            primitive_registry: PrimitiveRegistry,
            grammar_profiles: GrammarProfileRegistry,
            search_hints: DeterministicSearchHints,
            spec: FlowPlanningSpec,
    ) -> FlowPlan:
        """Build a deterministic runtime flow from canonical task grounding and active registries."""
        ...

    @abstractmethod
    def normalize_run_distill(
            self,
            draft_run_distill: DraftRunDistill,
            run_trace: RunTrace,
            spec: RunDistillNormalizationSpec,
    ) -> RunDistill:
        """Map draft post-run distillation into a canonical learning signal by enforcing trace-grounded validation."""
        ...
