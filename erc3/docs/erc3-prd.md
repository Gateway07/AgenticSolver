# PRD: AgenticSolver Methodology for ERC3-Style Benchmarks

## 1. Purpose

Define a methodology and target architecture to solve ERC3-style benchmark tasks (e.g. `erc3-prod`) using an AI agent with minimal human involvement.

The system must:

- Convert unstructured wiki + primitive external API endpoints into a deterministic, validated local knowledge base.
- Solve tasks through a strict `propose()` / `execute_and_validate()` split:
	- `propose(task, experience) -> plan` is LLM-driven.
	- `execute_and_validate(task, plan) -> decision` is deterministic and trusted.
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

Authoritative identity + time context:

- `who_am_i()` is the only authoritative identity source for access control and audit.
- `who_am_i()` is the only authoritative source of the run-time date context ("today") and wiki digest fields.

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
	- Deterministic outcome-selection rules (e.g., `ok_not_found` vs `none_clarification_needed` vs `none_unsupported`) derived from wiki policy
	- Deterministic formatting strictness rules (e.g., tasks that require exact `Yes`/`No` message bodies) derived from wiki policy

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

System boundary / single source of truth:

- **SQL snapshot is the authoritative data source during solving**.
- `execute_and_validate()` is allowed to mix snapshot + on-demand fetch **only when the snapshot is insufficient** to resolve the task.
	- Any on-demand fetch results must be persisted (or materialized) into SQL before being used in final computations.
	- The benchmark data is assumed **static during a single task run**, so on-demand fetch does not break determinism within that task.
- The wiki is treated as **immutable input during a single task run** (see `prd-api-acquisition.md` for digest handling and `prd-wiki-acquisition.md` for wiki
  rules).

**Output of Process A**:

- Normalized entity tables in SQL.
- A compact policy/constraint model in `policy.py`.
- A compositional tool framework in `tools.py`.

## 5.2 Process B - Building Execution Plan (algorithmic)

**Goal**: convert an untrusted natural-language task into a strict, machine-executable `Plan` that encodes:

- an algorithmic solution (what tool calls + what SQL computations)
- a response construction template (what outcome + which links are allowed)
- a proof carrier (commitments + policy references) sufficient for `execute_and_validate()` to verify correctness after execution

Trust boundary:

- Process B is LLM-driven and **untrusted**.
- Process B must not contribute evidence.
	- All evidence is produced later by Process C when the validator executes tool calls, persists payloads to SQL, runs SQL, and fills outputs.

Inputs:

- `InputTask.text`
- `DataDefinitionContext` (DDL view of the available entity tables/columns)
- compiled policy/constraints (from Process A)
- compositional tool facade (from Process A)
- `ExperienceStore` (optional) for adoptable planning rules

Output:

- `Plan` (exactly the Pydantic model in `agent/abstract.py`)

### B1. Plan as algorithmic solution + proof carrier

A `Plan` is the algorithmic solution to produce a valid response under policy:

- **Solution**:
	- an ordered set of tool calls (`execution_trace.calls`)
	- an ordered set of SQL computations (`facts` as `FactQuery`)
	- a strict response construction template (`response_template`)
- **Proof carrier**:
	- `policy_refs` identifies which policy clauses are intended to justify the decision
	- `commitments` declare proof obligations that Process C will verify after execution

Evidence restrictions (normative):

- `APICall.response`, `APICall.response_hash`, `APICall.error` must be empty in the Plan produced by `propose()`.
- `FactQuery.output` must be empty in the Plan produced by `propose()`.

### B2. Formal Plan schema (normative)

The Plan schema is defined by `agent/abstract.py` and must satisfy:

- `request`: the input task.
- `execution_trace`:
	- `calls`: ordered list of planned tool-level calls (`APICall`). Each item must include:
		- `id`: stable step identifier (string)
		- `tool`: tool facade name (must exist in `tools.py`)
		- `args`: JSON object of tool arguments
		- `expect`: optional expected result type identifier (for deterministic type-checking)
		- `bind`: optional symbolic name under which Process C stores the tool result for later SQL/response steps
	- `artifacts`: must be empty at propose-time (populated only by Process C).
- `facts`: ordered list of SQL-only computations (`FactQuery`):
	- `query`: SQL statement (read/derive)
	- `inputs`: references to previous fact ids (for deterministic dependency ordering)
	- `output`: must be empty at propose-time (populated only by Process C).
- `response_template`: strict template describing:
	- candidate `outcome` (or outcome selection rule)
	- message formatting constraints
	- link constraints (allowed kinds, inclusion/exclusion constraints)
- `dry_run`:
	- if `true`, Process C must validate permissions/parameters and render a response without executing writes.
	- if `false`, Process C may execute writes after passing all guardrails.
- `policy_refs`:
	- `rules_ids` may be empty, but if present must refer to rules that exist in compiled policy.
- `commitments`:
	- list of proof obligations to be verified by Process C.
	- `CommitmentKind` is intentionally extensible and may evolve.

### B3. Planning algorithm (normative)

Process B must produce a plan that is executable and verifiable.

Required steps:

- **B3.1 Interpret the task into a deterministic intent**
	- Extract entity types, identifiers, dates, and whether writes are requested.
	- If required inputs are missing and cannot be derived deterministically, the plan must target `none_clarification_needed` via `response_template`.

- **B3.2 Select tool calls (tool-level, deterministic, minimal)**
	- Tool calls must use the tool facade names and argument shapes.
	- The plan should start with `whoami()` whenever authorization context is required.
	- Paging must be planned deterministically (adoptable rules), e.g. `limit=5` with monotonic offsets.
	- Disambiguation must be planned deterministically:
		- if multiple plausible matches remain after deterministic narrowing, stop and plan a clarification outcome.

- **B3.3 Select SQL computations (`FactQuery`)**
	- Aggregation and final computations must be expressed in SQL (Process C executes SQL, not the LLM).
	- Fact queries must be ordered and reference dependencies via `inputs`.

- **B3.4 Write safety planning (when writes exist)**
	- A plan contains writes iff `execution_trace.calls` contains at least one tool call whose `tool` is classified as a write-capable tool by the compiled policy/tool facade.
	- The Plan must not rely on a separate `writes` list; write intent is inferred from tool calls.
	- The plan must include read-after-write verification steps when required by policy or by adoptable rules.
	- The plan must be compatible with `dry_run=true` (i.e., validation can occur without executing writes).

- **B3.5 Response template planning**
	- Specify message constraints and link constraints.
	- Ensure the template is compatible with response-structure policy (outcome semantics + link rules).

- **B3.6 Proof planning via commitments**
	- Commitments must be sufficient for Process C to prove:
		- trace integrity (calls executed in the declared order)
		- policy compliance
		- link grounding (links correspond to executed tool outputs)
		- write safety (for writes)
		- minimality (for non-`ok_answer` outcomes)
	- Commitment kinds are dynamic and may evolve over time.

### B4. Adoptable planning rules mechanism (recommended)

Process B should use an experience-driven, adoptable set of planning rules. Examples aligned with `docs/test-cases.md`:

- **Paging rule**: enforce `limit=5` and deterministic offset chaining until completion.
- **Name-order fallback rule**: try both “Last First” and “First Last” when searching people.
- **Query broadening/narrowing rule**: if a narrow query yields no results, retry with a broader paraphrase.
- **Clarify-on-ambiguity rule**: if multiple plausible matches remain, plan a clarification outcome instead of guessing.
- **Read-after-write rule**: when mutating state, include deterministic postcondition checks (e.g., re-fetch project/team).
- **Literal-execution rule**: execute user-requested values literally when policy allows, even if they look contradictory.

These rules must remain deterministic at execution time: Process C may apply them only as declared by the plan (no hidden retries).

## 5.3 Process C — Entity Constrained Execution & Validation

**Goal**: ensure every produced decision is compliant with explicit and implicit constraints, using deterministic validation.

### C1. Entity modeling

- Each API payload is converted to a Pydantic model.
- Validation must cover:
	- **Schema constraints**: required fields, types, enums.
	- **Normalization constraints**: canonical casing, ID formats, sorted lists where required.

### C2. Cross-entity constraints

- Enforce invariants derived from wiki and benchmark conventions:
	- Access constraints (deny when caller lacks permission).
	- Domain constraints (e.g. deal phases set; time entry status lifecycle constraints).
	- Aggregation constraints (workload is computed from project time slices, not from time logs).

### C3. SQL persistence and reproducibility

- Persist all entities and derived relations:
	- Raw entities: employees/customers/projects/time entries/wiki pages.
	- Derived tables/views: workload per employee, project-team join, skill/will index.
- Persist the full evidence trail needed to re-run validation deterministically.

### C4. Decision validation

`execute_and_validate(task, plan)` must check:

- Plan execution trace consistency (tools invoked as declared, inputs/outputs recorded).
- Correctness of derived computations (SQL queries are the only allowed aggregation engine).
- Response format compliance (outcome + links types) according to the policy acquired from the wiki.
	- This includes strictness requirements for message text where the policy demands it.
	- This includes deterministic outcome-selection rules (e.g., when to return `ok_not_found` vs `none_clarification_needed`).

**Output of Process C**:

- `decision` with:
	- `ok` flag
	- validated response
	- deterministic diagnostics (codes + structured context)

## 5.4 Process D — Task Solving Optimization

**Goal**: improve task success rate and determinism by using benchmark feedback as an objective signal.

Optimization is explicitly split into two loops:

### D1. Run-time optimization (inner loop)

- Trigger: after each task attempt (or after a scored test task), produce a patch that improves subsequent tasks.
- Allowed changes at run-time:
	- Update *experience* only (structured patches/heuristics), not core policies.
	- Adjust acquisition strategy (prefetch scope, query expansion, disambiguation prompts).
	- Tighten validation templates and response formatting.

### D2. Design-time optimization (outer loop)

- Trigger: after a full benchmark run.
- Allowed changes:
	- Modify `tools.py` composition logic.
	- Modify `policy.py` entity models and deterministic constraints.
	- Add/adjust SQL schema, indexes, derived views.
	- Add regression tests based on observed failure diagnostics.

### D3. Objective and metrics

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
	- Plan contains a strict schema (see Process B) and is treated as **untrusted** until `execute_and_validate()` executes and verifies it.

- `decision = execute_and_validate(task, plan)`
	- Executes the plan deterministically.
	- **Validator executes tool calls itself**: the LLM only outputs instructions; it does not supply data values that are treated as evidence.
	- Validates policy/security constraints.
	- Emits a response in the required structure.

### 7.1.1 Formal Plan schema (normative)

The normative Plan schema is defined in **Process B** and implemented as a Pydantic model in `agent/abstract.py`.

### 7.1.2 Tool execution trace (normative)

For every executed tool call, `execute_and_validate()` must record a trace entry with:

- tool name + arguments
- success/failure outcome
- stable identifiers and/or hashes of the returned payload

This trace is the evidence base used by `execute_and_validate()` when producing diagnostics.

### 7.1.3 SQL allowances (normative)

- SQL is the only allowed aggregation/derivation engine for final computations.
- SQL steps may include:
	- read-only `SELECT`
	- derived-table creation for deterministic computation (`derive` steps; e.g. `CREATE TEMP TABLE ... AS SELECT ...`, `INSERT INTO derived_* ... SELECT ...`).
- Schema evolution is not part of the run-time contract:
	- the session DB schema is recreated per task run, and derived tables are owned by the validator runtime.

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

Determinism assumptions:

- Benchmark data is static within a single task run.
- Wiki is immutable within a single task run.

## 8. Security and Compliance Requirements

- Enforce role-based access constraints; deny restricted data with `denied_security`.
- Never expose confidential fields (e.g. exact salaries) to unauthorized users.
- Treat wiki editing and system updates as privileged actions; validate caller authorization.
- Ensure outputs are free of sensitive leakage when returning `error_internal`.

Authorization context (normative):

- The authorization context comes exclusively from `who_am_i()`.
- For every allow/deny decision, validator must be able to produce a proof bundle containing:
	- the relevant identity fields from `who_am_i()` used by the rule
	- the specific rule reference(s) (wiki source page + anchor, or the compiled policy rule ID)
	- the evaluated predicate result (allow/deny)

Write operations guardrails (normative):

- Write actions are executed by the validator during plan execution (never by `propose()` directly).
- Validator must implement a dry-run mode:
	- validate intent-class + permissions + parameter shapes without applying the mutation.
- Validator must refuse writes that do not match an allowed operation class derived from the wiki policy (prompt-injection resistance).
	- Task text is treated as untrusted input; only explicit allowed intents may produce writes.

## 9. Acceptance Criteria

- **A1 (Acquisition)**: system can build a local SQL snapshot of core entities using paged API calls and can answer representative query families using only SQL
  transformations.
- **B1 (Validation)**: invalid plans or policy violations are rejected deterministically with structured diagnostics.
- **B2 (Response contract)**: every response is valid and uses only allowed format and structure.
- **C1 (Run-time optimization)**: after receiving a failing evaluation, the system can generate an experience patch that changes subsequent plans without
  modifying authoritative policies.
- **C2 (Design-time optimization)**: diagnostics are sufficient to reproduce failures and add regression tests that prevent recurrence.

## 10. ExperienceStore and patch governance (normative)

Experience is an optimization artifact and must not become an uncontrolled policy override.

### 10.1 Patch taxonomy (based on `rules/evolution-of-patches.md`)

Experience patches observed in practice cluster into these categories:

- **Rule patches** (`add_rule`, `remove_rule`, `consolidate_rules`)
	- permission rules (e.g., salary confidentiality, role-derived permissions)
	- response-contract rules (strict `links` behavior per outcome)
	- disambiguation rules (multiple matches → clarification)
	- operational rules (fail-fast after consecutive API errors)
- **Tool patches** (`patch_tool`, `update tool_patch`)
	- parameter name fixes (e.g., `employee` vs `id`)
	- required parameters (e.g., time logging requires specific fields)
	- endpoint semantics (e.g., replace-vs-add behavior)
	- per-endpoint constraints (e.g., pagination limits)
- **Prompt/process patches** (base algorithm restructuring, phase ordering)
	- enforce stable solving order: context gathering → permission check → retrieval → formatting

### 10.2 Consolidation and conflict resolution

The patch stream contains duplicates and contradictions; therefore ExperienceStore must support:

- deterministic de-duplication (same intent/signature)
- consolidation of overlapping patches into a single canonical guidance
- explicit conflict resolution with **newer patch priority** when patches contradict (as reflected by the consolidation notes in `evolution-of-patches.md`)

### 10.3 Governance constraints

- Experience may influence `propose()` behavior (tool selection, search strategy, formatting templates).
- Experience must not weaken validator constraints:
	- it cannot bypass access control
	- it cannot relax response contract validation
	- it cannot convert a denied action into an allowed write
- Validator must be able to report whether an Experience patch influenced a plan decision (auditability).

## 11. Evaluation and regression testing

- Benchmark evaluation is external.
- Minimal automated regression suite should be able to:
	- run a selected set of benchmark tasks end-to-end against the external API
	- store and compare evaluator outcomes/scores for regressions
	- use recorded execution traces to reproduce failures deterministically when the API data is unchanged

## 12. Operational constraints

- No explicit budgets/limits are assumed by the methodology.
- The validator must still prevent non-termination (e.g., fail-fast policies after repeated API errors) to ensure bounded runtime.
