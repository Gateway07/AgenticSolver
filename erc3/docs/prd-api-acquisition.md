# PRD: API Capability Acquisition (Process A2) + Deterministic Snapshot Acquisition (Process A3)

## 1. Purpose

Define the architecture and deterministic requirements for **Process A2** and **Process A3** from `AgenticSolver/prd.md`.

- **A2 (API capability acquisition)**: build a deterministic, machine-readable “API composition map” for `erc3-prod` based on `erc3.erc3.client.Erc3Client`.
- **A3 (deterministic snapshot acquisition)**: build deterministic, per-run snapshots of core entities and store them in a session SQLite database, with a
  streaming mode for large datasets.

System boundary:

- The SQL snapshot is the default and authoritative data substrate for computations.
- The benchmark data is assumed static within a single task run.

This PRD treats the existing files as **etalons (target artifacts)** that must be reproducible via automated Process A (no human intervention):

- `AgenticSolver/agent/erc3-prod/policy.py`
- `AgenticSolver/agent/erc3-prod/tools.py`

## 2. Scope

### 2.1 In scope

- **Target API**: `erc3-prod` only.
	- Source client: `erc3.erc3.client.Erc3Client`.
- Policy/schema acquisition requirements that explain how `policy.py` should be generated to mirror authoritative API DTO fields and enum domains.
- Wrapper requirements for:
	- `PrimitiveErc3APIClient`
	- `MemoryErc3Client`
	- `SQLErc3Client`
- Snapshot persistence:
	- SQLite session DB in `./.jbeval/`
	- Fresh DB per run
	- Streaming acquisition (incremental paging + buffered inserts; never hold full snapshots in memory)
- Deterministic task-derived date-range detection for time-entry/time-summary snapshot calls.

### 2.2 Out of scope

- Wiki snapshot persistence (wiki is treated as static content and handled by `AgenticSolver/prd-wiki-acquisition.md`).
- Persisting API call traces to SQL. Traces must exist, but remain in-memory.
- Any “business logic” beyond deterministic normalization, indexing, and persistence.

### 2.3 Wiki API optionality via `UserContext.wiki_sha1` (important note)

- Wiki APIs are treated as **optional** for snapshotting/persistence because wiki content is treated as **static** within a run/session based on the digest
  field `UserContext.wiki_sha1`.
- Heuristic rule:
	- If an environment exposes a **digest hash attribute** (e.g. `wiki_sha1`), the wiki corpus must be treated as **static** until the next time that digest
	  value changes.
- Change detection:
	- If `wiki_sha1` changes between runs, the system must treat this as a wiki corpus change event.
	- On a change event, the **Wiki Rule Acquisition** process (Process A1) must be restarted.
- Incremental restart via Wiki diff:
	- The restart must be driven by a **Wiki diff** between the previous and new wiki corpus versions.
	- Wiki diff is the mechanism for **incremental Wiki Rule Acquisition**: re-acquire/validate rules based on the delta only (changed/added/removed
	  pages/sections), while preserving unaffected rules.

## 3. Inputs

- **External API client**:
	- `erc3.erc3.client.Erc3Client`
	- DTO module `erc3.erc3.dtos` (for request/response shapes)
- **Etalon schema**: `AgenticSolver/agent/erc3-prod/policy.py`
- **Etalon wrappers**: `AgenticSolver/agent/erc3-prod/tools.py`
- **Task catalog**: `AgenticSolver/rules/tasks.md` (used to validate date-range extraction coverage)
- **Runtime context**:
	- `who_am_i()` response provides `today` and `wiki_sha1` and is the sole source of “current date”.

Additional invariants:

- `who_am_i()` is the only authoritative identity source (authorization context).
- Any non-snapshotted API fetches performed during validation must be treated as evidence and materialized into SQL before final computations.

## 4. Outputs

### 4.1 A2 Output: API composition map

A deterministic artifact (e.g., JSON) describing:

- Which endpoint returns which entity type(s).
- Which fields are authoritative per entity.
- Which endpoints must be chained for common query patterns.
- Paging semantics (offset/limit, `next_offset`) and determinism constraints.
- Update endpoints and their write-safety implications.

### 4.2 A3 Output: session snapshot database

A session SQLite database (fresh per run) stored under `./.jbeval/` containing:

- Normalized entity tables (employees, customers, projects, time entries, time summaries).
- Derived/normalized relational tables (project team allocations; employee skills/wills).
- Metadata table(s) describing acquisition configuration and provenance.

Authoritativeness and on-demand fetch:

- Snapshot tables are authoritative for deterministic computation.
- If the snapshot is insufficient to resolve a task, `validate()` may execute additional API calls and then persist/materialize their results into SQL.

## 5. Requirements — A2: API capability acquisition

### 5.1 Deterministic extraction

- The A2 builder must produce the composition map **deterministically** from:
	- `erc3.erc3.client.Erc3Client` method signatures and dispatch routes
	- `erc3.erc3.dtos` request/response models
- No trial API calls are allowed to “discover” capabilities.
- The composition map must be stable across runs given the same installed `erc3` package version.

### 5.2 Canonical capability inventory (erc3-prod)

The composition map must include at minimum:

- Core:
	- `who_am_i`
	- `provide_agent_response`
- Employees:
	- `list_employees`, `search_employees`, `get_employee`, `update_employee_info`
- Wiki (capabilities only; snapshotting optional/out-of-scope for A3 persistence):
	- `list_wiki`, `load_wiki`, `search_wiki`, `update_wiki`
- Customers:
	- `list_customers`, `search_customers`, `get_customer`
- Projects:
	- `list_projects`, `search_projects`, `get_project`, `update_project_team`, `update_project_status`
- Time tracking:
	- `log_time_entry`, `update_time_entry`, `get_time_entry`, `search_time_entries`
	- `time_summary_by_project`, `time_summary_by_employee`

### 5.3 Composition guidance (chaining)

The map must encode canonical chains for common intents, e.g.:

- **Project lead lookup**:
	- search/list projects → project.team → join employees by `Employee.id`
- **Workload computations** (policy-driven):
	- use `Project.team[].time_slice` as the authoritative workload substrate
- **Customer contact / account manager queries**:
	- search/list customers → `Company.account_manager` → join employee
- **Time entry auditing/creation**:
	- derive date range from task → snapshot time entries within range → (optional) validate with `time_summary_*`

### 5.4 Authoritative fields policy

The map must mark:

- **Primary keys**: `Employee.id`, `Company.id`, `Project.id`, `TimeEntry.id`.
- **Foreign keys**:
	- `Project.customer -> Company.id`
	- `Workload.employee -> Employee.id`
	- `TimeEntry.employee/customer/project -> respective ids`
- **Sensitive fields** (classification only; data is still stored):
	- `Employee.salary`
	- any sensitive content inside free-text notes fields

## 6. Requirements — Policy/schema acquisition (etalon: policy.py)

### 6.1 Closed-world ontology rail

- `policy.py` defines the closed-world set of:
	- entity models
	- enum domains
	- field types
	- semantic constraints encoded as Pydantic types
- Any wrapper output must be normalized into these models.

### 6.2 Automated generation requirement

- Process A must be capable of generating `policy.py` automatically from the external API’s DTOs.
- The generated schema must be stable and compatible with downstream uses:
	- validation
	- SQL persistence
	- deterministic joins

### 6.3 Backward compatibility

- Wrappers must remain compatible with both Pydantic v1 and v2 runtime conventions.
	- Example: support `model_validate/model_dump` (v2) and `parse_obj/dict` (v1).

## 7. Requirements — Wrapper layers

### 7.1 PrimitiveErc3APIClient (etalon)

**Goal**: a thin, typed wrapper over `Erc3Client` that normalizes all DTO responses into `policy.py` Pydantic models.

Requirements:

- Deterministic behavior only:
	- no retries with randomness
	- no heuristic business logic
- Each method must:
	- call exactly one `Erc3Client` method
	- convert the response to the corresponding `policy.py` model(s)
- Paging normalization:
	- list/search endpoints must return a normalized page object with `items` and `next_offset`.

### 7.2 MemoryErc3Client (etalon + SQL snapshot responsibility)

**Goal**: provide a fast, cached facade for testing and small datasets by prefetching entity snapshots for a run and exposing a cached `UserContext`, while also
persisting the snapshot in the session SQLite DB.

Mandatory prefetched data (wiki excluded):

- `UserContext` via `who_am_i`
- Employees via paging
- Customers via paging
- Projects via paging

Task-derived / optional prefetched data (depends on dataset size and selected client):

- Time entries via paging (task-derived date range)
- Time summaries (by project and by employee; same date range)

Additional requirements:

- **Deterministic call order**:
	- `who_am_i` must be called first.
	- registry paging must use stable `offset` progression until `next_offset is None`.
- **Reference population**:
	- cross-links (customer.projects, project.customers)
	- time entry fan-out to employee/customer/project
	- time summary fan-out to employee/project
- **SQL snapshot write-through**:
	- after each page is fetched, buffer rows and flush to SQLite per policy batch sizes.
	- never require holding the full entity set in memory to persist it.

Caching scope (normative):

- Wiki content is static per benchmark session (bounded by `wiki_sha1`).
- Non-wiki entity snapshots are treated as per-task-run (fresh DB per run).
- In-memory caching to avoid repeated remote calls is allowed within a single task run.

## 8. Requirements — A3: session snapshot persistence

### 8.1 Session DB

- Engine: SQLite.
- Location: `./.jbeval/`.
- Lifecycle: **fresh DB per run**.
	- No upserts required if the DB is always created new.
- The DB contains sensitive data as returned by the API (no redaction at storage time).

### 8.2 SnapshotAcquisitionPolicy (pydantic config)

A pydantic schema (configuration rail) must define at minimum:

- SQLite:
	- database root path (default `./.jbeval/`)
	- db filename format (must be unique per run)
- Paging:
	- `page_limit`
- Insert buffering:
	- `insert_batch_size_rows`
	- `max_buffer_rows` (hard guard)
- Deterministic ordering:
	- `order_by_id_before_insert: bool`

### 8.3 Normalized SQL schema

The snapshot DB must store, at minimum:

- `employees`
- `employee_skills`
- `employee_wills`
- `customers`
- `projects`
- `project_team` (one row per workload allocation)
- `time_entries`
- `time_summaries_by_project`
- `time_summaries_by_employee`
- `snapshot_meta` (run metadata)

Constraints:

- Primary keys must match the authoritative IDs.
- Foreign keys must be preserved as columns (SQLite FK enforcement optional, but schema must be relationally correct).
- JSON fields are allowed only when the source cannot be normalized without information loss; otherwise normalize into tables.

## 9. Requirements — SQLErc3Client (streaming snapshot client)

**Goal**: provide a client facade that performs snapshot acquisition and writes directly to the session SQLite DB using incremental paging and buffered inserts.

Requirements:

- Must use `PrimitiveErc3APIClient` as the exclusive remote-call primitive.
- Must never require holding the full snapshot (any entity type) in memory.
- Must support buffered inserts:
	- fetch one page → convert to `policy.py` model(s) → stage rows → insert when batch threshold is reached.
- Must record acquisition provenance in `snapshot_meta`:
	- base_url
	- `who_am_i` digest fields (`today`, `wiki_sha1`)
	- selected `date_from/date_to`
	- `SnapshotAcquisitionPolicy` serialized form

On-demand fetch during validation:

- If `validate()` needs additional data beyond the prefetched snapshot, it may call the same primitive API methods and then insert the returned entities into SQL
  (either into existing normalized tables or into validator-owned derived tables).

## 10. Deterministic task-derived date range detection

### 10.1 Inputs

- Task text (natural language)
- `today` from `who_am_i()` (single authoritative “now”)

### 10.2 Output

- `date_from: YYYY-MM-DD`
- `date_to: YYYY-MM-DD`

### 10.3 Deterministic parsing rules

The detector must be deterministic and rule-based (no model calls). It must support, at minimum:

- Explicit ISO date: `YYYY-MM-DD`
- Relative dates:
	- `yesterday`
	- `two days before yesterday`
	- `last week`
	- `last week` with ISO-week semantics (Mon..Sun) relative to `today`
	- `last week` / `a week ago` must resolve unambiguously using `today`

If no date information exists in task text:

- Set `date_from = today` and `date_to = today`.

The selected date range must be the minimal range that covers all detected referenced dates.

## 11. Trace requirements (in-memory only)

Even though snapshots are persisted to SQLite, wrappers must also support in-memory traceability:

- Record each API call in an in-memory `ExecutionTrace` structure (request params + response payload and/or response hash).
- SQL persistence must not be required to reconstruct the trace.

## 12. Acceptance criteria

- **AC-A2-1**: The composition map includes all required `Erc3Client` capabilities and their entity mappings.
- **AC-A2-2**: The composition map is deterministic across repeated runs with the same `erc3` package version.
- **AC-A3-1**: A fresh SQLite snapshot DB is created under `./.jbeval/` per run and contains all mandatory entity tables.
- **AC-A3-2**: Snapshot acquisition uses paging for all registry endpoints until `next_offset is None`.
- **AC-A3-3**: `SQLErc3Client` never requires holding a full entity snapshot in memory (validated by code inspection + configurable buffer guards).
- **AC-A3-4**: Date range detector returns deterministic `date_from/date_to` for tasks containing relative phrases and defaults to `today..today` otherwise.
- **AC-A3-5**: Snapshot DB contains sensitive fields as returned by the API (no storage-time redaction).
- **AC-A3-6**: Memory prefetch populates cross-references deterministically and does not introduce additional API calls after the prefetch phase (except
  explicit write operations).
