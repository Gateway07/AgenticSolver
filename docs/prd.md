# PRD — Autonomous Framework for Unknown-In-Advance-API Benchmark Tasks

## 0. Goal

Build a framework that solves benchmark-style tasks with an **unknown in advance API** and **no human in the loop**.

The system must:

* start from only a raw benchmark rules HTML page URL,
* discover structure and constraints automatically,
* synthesize design-time artifacts,
* assemble and execute deterministic runtime flows,
* improve itself through closed feedback loops.
* use Codex CLI for LLM calls

---

## 1. Problem Statement

The framework receives:

* a URL to a raw HTML page containing rules and benchmark description,
* a fixed set of preinstalled tools (Python runtime, SQL database, bash, etc.),
* no domain-specific code, no human annotations, no manual API integration.

The framework must autonomously:

1. infer the task environment,
2. derive machine-usable knowledge,
3. synthesize executable design-time artifacts,
4. build and execute deterministic runtime plans,
5. learn from outcomes and improve over time.

---

## 2. System Model

The system is organized into four processes.

### A. Memory Acquisition

Purpose:

* discover sources from the initial HTML page,
* distill domain memory from raw text and discovered documents,
* normalize it into canonical machine-usable memory.

See also: [Process A — Memory Acquisition (Detailed Plan)](./prd_acquisition.md)

Outputs:

* source inventory,
* domain memory,
* runtime ontology,
* alias maps,
* failure catalog.

### B. Design-Time Synthesis

Purpose:

* generate and refine design-time artifacts from canonical memory and accumulated evidence.

Outputs:

* typed intermediate representation (IR),
* primitive candidates,
* search hints,
* templates,
* compiled code artifacts (Python / SQL / Rego),
* promoted registries.

### C. Runtime Planning

Purpose:

* ground a task into typed control signals,
* build a deterministic flow from allowed primitives and active registries.

Outputs:

* grounded task frame,
* deterministic search hints,
* replayable flow plan.

### D. Deterministic Execution

Purpose:

* execute the flow,
* record immutable trace,
* distill outcome into reusable feedback.

Outputs:

* run trace,
* verified run distill,
* new feedback for A/B.

---

## 3. Self-Adaptive Loops

The framework operates as three nested self-adaptive loops.

### Inner Loop — Run-Time Optimization

Scope: C + D
Frequency: every task run

Responsibilities:

* task grounding,
* deterministic flow planning,
* execution,
* trace capture,
* run-level distillation.

Objective:

* maximize task success,
* minimize runtime cost,
* preserve policy and replayability constraints.

### Outer Loop — Design-Time Optimization

Scope: B
Frequency: periodic or evidence-triggered

Responsibilities:

* build or extend abstraction corpus,
* induce and normalize abstraction candidates,
* synthesize design IR,
* compile artifacts,
* verify artifacts,
* promote verified design updates.

Objective:

* improve reusable abstractions,
* reduce runtime search complexity,
* increase success without regressions.

### Main Loop — Solution Optimization

Scope: A + loop orchestration
Frequency: rare or strategic

Responsibilities:

* improve memory acquisition,
* improve source interpretation,
* improve domain distillation quality,
* decide when outer-loop redesign is needed.

Objective:

* improve long-term system quality and adaptation capacity.

---

## 4. Initial Conditions

At the beginning of process A, the system has only:

* preinstalled general-purpose tools,
* a URL pointing to a raw HTML page with benchmark rules and description.

No benchmark-specific adapters, schemas, registries, or domain logic are assumed.

The initial HTML page is treated as raw input. The system must first:

1. fetch it,
2. extract raw text blocks and links,
3. semantically interpret what source groups may exist,
4. discover additional documents from that interpretation.

---

## 5. Function Classes

The system uses three function classes.

### Class 1 — Ready-Made General-Purpose Deterministic Functions

Trusted infrastructure available before domain discovery.

Examples:

* fetch raw HTML and documents,
* structural schema validation,
* template-based code compilation,
* registry persistence,
* deterministic verification harness,
* deterministic executor,
* deterministic promotion and persistence.

These are part of the fixed bootstrap kernel.

### Class 2 — Deterministic Abstract Placeholders

Generic engines with fixed control logic, but domain semantics are provided later through design-time artifacts and specs.

Examples:

* normalize discovered sources,
* normalize domain memory,
* retrieve memory slice,
* build or extend abstraction corpus,
* normalize abstraction proposals,
* normalize design IR,
* generate coverage cases,
* update regression cases,
* normalize task grounding,
* resolve runtime search hints,
* build deterministic flow plans,
* normalize post-run distillation.

These functions do not contain hardcoded business logic. They become meaningful only after process B provides specs, registries, and typed artifacts.

### Class 3 — Non-Deterministic LLM Functions

LLM-owned semantic synthesis.

Responsibilities:

* discover source groups from raw HTML,
* distill domain memory,
* induce abstraction proposals,
* synthesize design-time IR,
* ground task text into typed labels,
* distill run outcomes.

Constraint:

* LLM outputs typed artifacts only.
* LLM does not emit trusted runtime logic directly.

---

## 6. Core Architecture

### Small Kernel

A minimal trusted bootstrap core.

Contains:

* fetch/load tools,
* structural validation,
* deterministic template-based compiler,
* registry persistence.

The kernel is fixed, small, and domain-agnostic.

### Meta-Interpreters

Trusted deterministic engines that interpret policies and specs.

Contains:

* generic verifier,
* generic executor,
* generic promotion engine.

Meta-interpreters do not encode domain logic themselves. They execute fixed algorithms over typed specs and compiled artifacts.

### LLM-Synthesized Artifacts

Produced in process B and consumed by deterministic layers.

Includes:

* source inventory drafts,
* domain memory drafts,
* abstraction drafts,
* design IR,
* search hints,
* templates,
* primitive candidates.

The kernel and meta-interpreters interpret these artifacts after deterministic normalization and verification.

---

## 7. Design-Time Extension Mechanism for Class 2

This is the key mechanism of the system.

### Principle

Class 2 functions are not rewritten manually and are not replaced by arbitrary generated code. Instead, they are extended by typed design-time artifacts
synthesized in process B.

### Extension Pattern

Deterministic behavior is defined as: **generic engine + validated typed spec + canonical state**
Not: **raw LLM-generated code**

### How Extension Happens

#### Step 1 — Bootstrap from Static Semantics

Before any runtime evidence exists, the system has:

* canonical domain memory,
* endpoint specs,
* ontology,
* alias maps,
* task patterns.

From this, process B synthesizes initial:

* primitive candidates,
* search hints,
* templates.

These create a seed design structure.

#### Step 2 — Seed Abstraction Corpus

Because runtime traces are initially empty, the first abstraction corpus is built from:

* task patterns,
* domain rules,
* endpoint contracts,
* seed primitive candidates,
* templates.

This corpus is hypothesis-driven, not evidence-driven.

#### Step 3 — Runtime Evidence Appears

After first runs, the system gets:

* grounded task frames,
* flow plans,
* run traces,
* run distills.

#### Step 4 — Corpus Extension

The seed abstraction corpus is extended with observed evidence:

* real fragment signatures,
* usage counts,
* success/failure links,
* repair patterns.

#### Step 5 — Design-Time Refinement

Process B uses the extended corpus to:

* refine abstraction proposals,
* synthesize improved design IR,
* compile new artifacts,
* verify and promote updates.

This is how Class 2 functions gain domain-specific power while remaining deterministic.

---

## 8. Runtime Safety and Determinism

The runtime layer must remain deterministic.

This requires:

* task grounding to produce typed control artifacts only,
* deterministic normalization after every LLM-produced runtime artifact,
* runtime flow construction as constrained search over allowed primitives,
* execution through compiled bindings only,
* immutable traces for every run.

No unrestricted runtime code generation is allowed.

---

## 9. Artifact Flow

### From A to B

Process A produces:

* source inventory,
* canonical domain memory,
* ontology,
* alias maps,
* failure catalog.

These become the semantic substrate for process B.

### Within B

Process B produces:

* abstraction candidates,
* search hints,
* templates,
* canonical design IR,
* compiled artifacts,
* promoted registries.

### From B to C

Process C consumes:

* primitive registry,
* search hints,
* grammar profiles,
* ontology,
* alias maps.

### From C/D back to A/B

Processes C and D produce:

* grounded task frames,
* flow plans,
* run traces,
* run distills.

These become feedback signals for future improvement.

---

## 10. Promotion and Control Rules

A system update must not become active just because it was generated.

Promotion requires:

* deterministic normalization,
* deterministic verification,
* explicit pass criteria,
* no regression against the frozen regression set,
* persistence with versioning and provenance.

Promotion and persistence are distinct:

* promotion is a semantic state transition,
* persistence is low-level storage of the resulting active state.

---

## 11. Theoretical Basis for Balancing Primitives vs Flow

The framework is based on a **multi-level constrained optimization** model:

* at process **B**, the system selects and improves the primitive library;
* at process **C**, the system builds runtime flows through deterministic search over an allowed list.

Core principle:

* a library that is too **small** produces long, fragile, and expensive flows;
* a library that is too **large** increases branching factor, complicates selection, and degrades search quality.

Therefore, the system must optimize **total solution complexity**, not only flow length or only library size.

The balance must consider:

* size and complexity of `PrimitiveRegistry`,
* average `FlowPlan` length,
* runtime execution cost,
* ambiguity in primitive choice,
* coverage across task classes.

Design-time decisions must follow this rule:

**A new primitive is added only if it reduces total solution complexity over the task distribution**, not merely because it shortens one isolated scenario.

Implications:

* reusable patterns are promoted into primitives;
* one-off or overly narrow compositions remain at the flow level;
* runtime search operates under profile constraints (`GrammarProfileRegistry`) rather than the full primitive universe.

This balance is a first-class design objective of the outer loop.

---

## 12. Statistical Check as Feedback Signal

The framework must use **statistical check** as a formal feedback signal for all self-adaptive loops.

Primary signal sources:

* `RunTrace`
* `RunDistill`
* `DesignVerificationReport`
* aggregated multi-run outcomes

Statistical check must evaluate not only single runs, but also **accumulated behavior across task classes**.

Minimum metrics:

* success rate,
* average score,
* cost per run,
* violation rate,
* average flow length,
* reuse frequency of new primitives,
* regression stability,
* performance on rare or hard task classes.

Use by loop:

### Inner Loop

Uses run-level and short-window statistics for:

* selecting more stable flows,
* ranking hints,
* constraining repair strategies.

### Outer Loop

Uses batch-level statistics for:

* deciding which abstraction candidates truly improve the system,
* pruning, merging, or extracting library elements,
* updating search hints and templates.

### Main Loop

Uses aggregate statistics across task classes for:

* deciding whether the system is improving globally,
* checking whether rare or long-tail scenarios are degrading,
* determining whether memory acquisition or design-time redesign must be revisited.

Critical rule:

* no system update is promoted from a single “good” result;
* promotion requires **stable improvement without regression** according to statistical check.

Statistical check is therefore not just an auxiliary metric. It is a **formal verifier signal for system change**.

---

## 13. Key Constraints

The framework must enforce:

* no human intervention after launch,
* no trusted business logic generated directly into runtime,
* all runtime execution must be replayable,
* all promoted changes must pass deterministic verification,
* all LLM outputs must be normalized into canonical typed artifacts,
* design-time learning must improve the system without uncontrolled drift.

---

## 14. Codex CLI client plan (LLM execution layer)

PRD requires using Codex CLI for LLM calls (PRD §0). Process A depends on LLM calls that must produce typed outputs.

### 14.1 Goal

Implement a client that runs:

- `codex exec --output-schema <schema_path>`

as a subprocess and returns a validated Pydantic object.

### 14.2 Contract

For each LLM function (e.g., `discover_source_inventory`, `distill_memory`):

- build a prompt (including only necessary context)
- provide the JSON Schema path corresponding to the Pydantic model
- parse stdout as JSON
- validate into Pydantic model

### 14.3 Guardrails

- **Timeouts**:
	- hard timeout per call
	- ensure subprocess termination on timeout
- **Retry + self-correction**:
	- retry only on actionable failures (non-zero exit, JSON parse error, Pydantic validation error)
	- include validation error summaries in the repair prompt
	- cap attempts and persist attempt history for provenance
- **Asynchrony**:
	- use async subprocess execution (`asyncio`)
	- enforce concurrency limits (semaphore)
	- cancellation must propagate to subprocess

### 14.4 Provenance

Persist per-call metadata:

- schema path + schema hash
- prompt hash
- attempt count and error summaries
- resulting typed artifact hash

## 15. Success Criteria

The framework is successful if it can:

1. bootstrap from only:
	
	* a raw HTML entry page URL,
	* preinstalled general-purpose tools;

2. autonomously construct:
	
	* canonical domain memory,
	* design-time IR,
	* compiled artifacts,
	* runtime plans;

3. execute tasks without human-written domain adapters;

4. accumulate reusable feedback and improve over time;

5. keep runtime deterministic while design-time evolves.

---

## 16. Non-Goals

This framework does not aim to:

* rely on manual API adapters,
* rely on manual curation of benchmark-specific logic,
* allow unrestricted runtime code generation,
* depend on a human reviewer for normal operation.

---

## 17. Final Product Definition

The product is a **self-adaptive autonomous framework** that combines:

* a small trusted kernel,
* deterministic meta-interpreters,
* LLM-based semantic synthesis,
* typed design-time artifacts,
* deterministic runtime planning and execution,
* multi-level feedback-driven improvement,

to solve unknown-in-advane-API benchmark-style tasks without human participation.
