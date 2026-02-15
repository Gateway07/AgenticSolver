# PRD: AgenticSolver Methodology for ERC3-Style Benchmarks

## 1. Purpose

Define a methodology and target architecture to solve ERC3-style benchmark tasks (e.g. `erc3-prod`) using an AI agent with minimal human involvement.

The system must:

- Convert unstructured wiki + primitive external API endpoints into a deterministic, validated local knowledge base.
- Solve tasks through a strict `propose()` / `validate()` split:
	- `propose(task, experience) -> plan` is LLM-driven.
	- `validate(task, plan) -> decision` is deterministic and trusted.
- Improve over time via a **double optimization loop**:
	- **Run-time**: between tasks in a single benchmark run.
	- **Design-time**: after a benchmark run, offline.

## 2. Scope

### 2.1 In scope

- Proactive information acquisition from:
	- Local Wiki (`AgenticSolver/wiki/*.md`, and `wiki_meta.json`).
	- External API client (`erc3.client.Erc3Client`): `who_am_i()`, `list_*()`, `search_*()`, `get_*()`, `update_*()`.
	- Task list references (`AgenticSolver/rules/tasks.md`).
- Entity normalization and persistence in SQL database.
- Deterministic constraint checking using Pydantic-based validation.
- Task-solving optimization via feedback-driven patches and evaluation metrics.

### 2.2 Out of scope

- Training or fine-tuning foundation models.
- UI/UX for chat.
- Manual curation of per-task answers (human should not craft solutions).

## 3. Inputs

### 3.1 Wiki

- Markdown pages representing policies, domain facts, and system rules.
- `wiki_meta.json` provides:
	- A stable list of wiki files and short summaries.
	- A benchmark task set overview.

### 3.2 External API

- API surface is large and primitive. It must be composed into higher-level operations.
- Key characteristics to plan for:
	- Paging (`offset`, `limit`) for list/search endpoints.
	- Mixed access constraints (some data is restricted).

### 3.3 Task stream

- Natural-language tasks, including:
	- Paraphrases, multilingual prompts, ambiguous entities.
	- Tasks requiring aggregation, joins, and comparisons.
	- Tasks requiring updates (employee/project/time/wiki).

## 4. Outputs / Artifacts

### 4.1 `tools.py` (external API framework)

A deterministic, testable tool layer that:

- Wraps primitive client calls into composable operations.
- Supports deterministic collection of complete datasets via paging (prefetch snapshots).
- Provides typed results and uniform error handling.

Required capabilities:

- **Composed queries**: e.g. “project by paraphrase -> project_id -> full project -> team -> employees -> derived aggregates”.
- **Deterministic prefetch**: bulk load employees/projects/customers/time entries where needed.
- **Caching**: avoid repeated remote calls inside the same task/round.
- **Audit trail**: record each call (request params, response hashes/IDs) for validation.

### 4.2 `policy.py` (policy + entities + constraints)

A deterministic validation kernel that:

- Encodes authoritative rules distilled from wiki.
- Defines Pydantic entity models and cross-entity invariants.
- Produces structured diagnostics for optimization.

It must represent:

- Input task contract
- Entities (examples): `Employee`, `Customer`, `Project`, `TimeEntry`, `WikiPage`, plus supporting types (`SkillLevel`, workload allocations, deal phases).
- Response contract:
	- Outcome format and required structure
	- Additional/optional link structures

## 5. Core Methodological Processes

## 5.1 Process A — Proactive Information Acquisition

**Goal**: proactively obtain the minimum sufficient set of facts and rules to solve tasks deterministically.

### A1. Wiki rule acquisition

- Parse and compress wiki content into a short, precise policy representation.
- The representation must be:
	- Minimal (only constraints and definitions needed for tasks).
	- Precise (lossless for constraints).
	- Referential (each rule should have a source page reference for traceability).

Examples of rule families to extract:

- **Access control** (e.g. salary visibility restrictions).
- **Workload definition**: workload is derived from project registry time-slice allocations.
- **Skills & wills scale**: 1–10; “strong” threshold is interpreted consistently (e.g. `>= 7`).
- **Entity field semantics** (deal phases, project status, time entry statuses).
- **Response formatting** (e.g. `outcome`, `links` fields).

### A2. API capability acquisition

- Build an internal “API composition map”:
	- Which endpoint returns which entity type.
	- Which fields are authoritative.
	- Which endpoints must be chained to answer typical queries.

### A3. Deterministic snapshot acquisition

- Use paging to collect stable local snapshots for deterministic processing (Employees, customers, projects, and optionally time entries).
- Use data prefetching to avoid repeated remote calls inside the same task/round.
- Data snapshot is stored in SQL database by using streaming (if external API is huge to load in memory) and becomes the default source for computation.

**Output of Process A**:

- Normalized entity tables in SQL.
- A compact policy/constraint model in `policy.py`.
- A compositional tool framework in `tools.py`.

## 5.2 Process B — Entity Constrained Validation

**Goal**: ensure every produced decision is compliant with explicit and implicit constraints, using deterministic validation.

### B1. Entity modeling

- Each API payload is converted to a Pydantic model.
- Validation must cover:
	- **Schema constraints**: required fields, types, enums.
	- **Normalization constraints**: canonical casing, ID formats, sorted lists where required.

### B2. Cross-entity constraints

- Enforce invariants derived from wiki and benchmark conventions:
	- Access constraints (deny when caller lacks permission).
	- Domain constraints (e.g. deal phases set; time entry status lifecycle constraints).
	- Aggregation constraints (workload is computed from project time slices, not from time logs).

### B3. SQL persistence and reproducibility

- Persist all entities and derived relations:
	- Raw entities: employees/customers/projects/time entries/wiki pages.
	- Derived tables/views: workload per employee, project-team join, skill/will index.
- Persist the full evidence trail needed to re-run validation deterministically.

### B4. Decision validation

`validate(task, plan)` must check:

- Plan execution trace consistency (tools invoked as declared, inputs/outputs recorded).
- Correctness of derived computations (SQL queries are the only allowed aggregation engine).
- Response format compliance (outcome + links types).

**Output of Process B**:

- `decision` with:
	- `ok` flag
	- validated response
	- deterministic diagnostics (codes + structured context)

## 5.3 Process C — Task Solving Optimization

**Goal**: improve task success rate and determinism by using benchmark feedback as an objective signal.

Optimization is explicitly split into two loops:

### C1. Run-time optimization (inner loop)

- Trigger: after each task attempt (or after a scored test task), produce a patch that improves subsequent tasks.
- Allowed changes at run-time:
	- Update *experience* only (structured patches/heuristics), not core policies.
	- Adjust acquisition strategy (prefetch scope, query expansion, disambiguation prompts).
	- Tighten validation templates and response formatting.

### C2. Design-time optimization (outer loop)

- Trigger: after a full benchmark run.
- Allowed changes:
	- Modify `tools.py` composition logic.
	- Modify `policy.py` entity models and deterministic constraints.
	- Add/adjust SQL schema, indexes, derived views.
	- Add regression tests based on observed failure diagnostics.

### C3. Objective and metrics

Primary success metric:

- Benchmark score (task-level correctness).

Secondary metrics:

- Determinism: variance of outputs across reruns given identical snapshots.
- Tool efficiency: number of external API calls per task.
- Validation quality: fraction of failures caught before submission.
- Coverage: fraction of tasks solvable from local SQL snapshot without extra remote calls.

## 6. Preparation and Improvement Phases

## 6.1 Acquisition Phase (pre-competition)

**Goal**: build the initial deterministic substrate.

Deliverables:

- `policy.py`: policies + Pydantic models + constraint checks.
- `tools.py`: compositional API tools + paging snapshot acquisition + caching.
- SQL database with entity snapshots and derived views.

Functional form:
Acquisition(Wiki, API, Tasks) -> policy.py, tools.py, SQL schema + initial snapshots

## 6.2 Run-time Phase (during competition)

**Goal**: improve performance within a run without human intervention.

Mechanism:

- Use the benchmark’s per-task feedback to update an `ExperienceStore`.
- Experience must remain non-sensitive and non-authoritative:
	- store diagnostics codes and safe guidance templates.
	- do not store raw confidential entity data.

## 6.3 Design-time Phase (between runs)

**Goal**: incorporate lessons learned into code and tests.

Mechanism:

- Offline analysis of:
	- validator diagnostics
	- tool traces
	- failure clusters by task families
- Produce code changes and regression suites.

## 7. Core Control Flow and Contracts

## 7.1 Plan/Decision dependency

- `plan = propose(task, experience)`
	- Output is **strict**, machine-executable instructions.
	- Plan contains:
		- Ordered `tools.py` calls to fetch missing data.
		- Ordered SQL statements/queries over local entities.
		- Evidence references (entity IDs, wiki rule references).

- `decision = validate(task, plan)`
	- Executes the plan deterministically (or replays recorded results).
	- Validates policy/security constraints.
	- Emits a response in the required structure.

## 7.2 Double-loop model

- Inner loop: repeated propose/validate rounds for the same task with updated experience.
- Outer loop: post-run code iteration over `policy.py` and `tools.py`.

## 7.3 Determinism boundary

- Only `propose()` is non-deterministic.
- All the following must be deterministic:
	- Tool execution engine and paging strategy.
	- SQL transformations.
	- Pydantic validation and policy checks.
	- Response formatting rules.

## 8. Security and Compliance Requirements

- Enforce role-based access constraints; deny restricted data with `denied_security`.
- Never expose confidential fields (e.g. exact salaries) to unauthorized users.
- Treat wiki editing and system updates as privileged actions; validate caller authorization.
- Ensure outputs are free of sensitive leakage when returning `error_internal`.

## 9. Acceptance Criteria

- **A1 (Acquisition)**: system can build a local SQL snapshot of core entities using paged API calls and can answer representative query families using only SQL
  transformations.
- **B1 (Validation)**: invalid plans or policy violations are rejected deterministically with structured diagnostics.
- **B2 (Response contract)**: every response is valid and uses only allowed format and structure.
- **C1 (Run-time optimization)**: after receiving a failing evaluation, the system can generate an experience patch that changes subsequent plans without
  modifying authoritative policies.
- **C2 (Design-time optimization)**: diagnostics are sufficient to reproduce failures and add regression tests that prevent recurrence.
