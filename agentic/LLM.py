from model import *


# ============================================================================
# LLM: Semantic synthesis only
# ============================================================================

class LLM:
    """All semantic synthesis owned by the LLM layer. Outputs are typed artifacts, never final runtime code."""

    def discover_source_inventory(self, initial_page: PageSnapshot) -> DraftSourceInventory:
        """Interpret the raw entry page and propose draft source groups for wiki pages, endpoint docs, and task references."""
        ...

    def distill_memory(self, raw_docs: list[SourceDocument], endpoint_docs: list[SourceDocument],
                       traces: list[RunTrace], failures: list[FailureRecord]) -> DraftDomainMemory:
        """Distill raw domain materials into draft semantic memory with rules, aliases, entities, and task patterns."""
        ...

    def induce_abstractions(self, corpus: AbstractionCorpus, primitive_registry: PrimitiveRegistry,
                            memory: DomainMemory, failures: list[FailureRecord]) -> DraftAbstractionSet:
        """Propose draft primitive candidates, search hints, and templates from observed runtime evidence."""
        ...

    def synthesize_design(self, slice: DomainMemory, promoted_candidates: list[PrimitiveCandidateIR],
                          endpoint_specs: list[EndpointSpec]) -> DraftDesignIR:
        """Synthesize draft design-time IR from canonical memory and promoted abstraction candidates."""
        ...

    def ground_task(self, task_text: str, domain_memory_slice: DomainMemory) -> DraftTaskFrame:
        """Convert task text into a draft typed runtime control frame for deterministic planning."""
        ...

    def distill_outcome(self, run_trace: RunTrace, task_text: str,
                        grounded_task_frame: TaskFrame) -> DraftRunDistill:
        """Compress a completed run into a draft learning signal for later deterministic validation."""
        ...
