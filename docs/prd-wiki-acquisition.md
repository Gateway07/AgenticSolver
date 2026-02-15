# PRD: Wiki Rule Acquisition (Process A1)

## 1. Purpose

Define the architecture and pipeline for **automated extraction of business rules from wiki content** into a compact, validated, traceable intermediate
representation (IR).
This PRD addresses section **A1 — Wiki rule acquisition** from the parent PRD and is built on three foundational requirements:

1. **Long-context handling via RLM pattern** — wiki files are treated as an external environment, not as a prompt payload; the agent accesses them
   programmatically through lazy loading, selective reading, and recursive delegation.
2. **ADK Python as the agentic framework** — tools, sessions, callbacks, evaluation, and the RLM sample
   from [adk-python](https://github.com/LiamConnell/adk-python) provide the reproducible orchestration skeleton.
3. **Entity ontology + task rails as hard constraints** — the existing Pydantic schema (`policy.py`) and the benchmark task list (`rules/tasks.md`) are
   converted into two mandatory rails that bound what the agent may extract and why.

Wiki immutability and digest boundary:

- Within a single task run, the wiki is treated as immutable input.
- Across task runs/sessions, wiki may change only when the environment signals a digest change (e.g., `UserContext.wiki_sha1`).
- If `wiki_sha1` is available, it is the only supported mechanism for deciding whether the wiki corpus has changed.

## 2. Inputs

### 2.1 Wiki corpus

Markdown pages under `AgenticSolver/wiki/` (~20 files, 2–10 KB each) plus `wiki_meta.json`.

If an environment exposes wiki APIs (`list_wiki`, `load_wiki`, `search_wiki`, `update_wiki`), the wiki corpus is treated as static within a session bounded by
`UserContext.wiki_sha1` (see `prd-api-acquisition.md`).

### 2.2 Entity ontology (Schema rail)

Source: `AgenticSolver/agent/policy.py` Pydantic models.
Closed-world constraint: the agent may only reference entities, fields, and enum values present in this ontology. Anything else → `missing_info`.

### 2.3 Task list (Task rail)

Source: `rules/tasks.md` (102 benchmark tasks).
Task families derived from the task list:

| Family                  | Example task IDs                                           | Required entities / fields                                                              |
|-------------------------|------------------------------------------------------------|-----------------------------------------------------------------------------------------|
| **access_control**      | t11, t16, t31, t37, t40, t44–t46, t55, t59, t63, t66, t83  | Employee.salary, Employee.department, WhoAmIContext.is_public, role-based visibility    |
| **workload_derivation** | t4, t9–t12, t76, t78–t79                                   | Project.team[].time_slice, Project.status, Employee.id                                  |
| **skill_will_query**    | t13–t14, t17, t56, t74–t77, t86, t94–t96                   | SkillLevel.name, SkillLevel.level, "strong" threshold                                   |
| **scale_threshold**     | t17, t56, t86                                              | SkillLevel.level ≥ 7 ↔ "strong"                                                         |
| **entity_lookup**       | t1–t3, t6–t8, t15, t26–t28, t38–t41, t43, t80–t82, t87–t93 | Employee.name, Project.name, Company.name, paraphrase resolution                        |
| **entity_update**       | t32–t36, t47–t55, t57–t59, t92, t97, t101                  | TimeEntry creation/void, Employee.notes, Employee.salary, Project.status, Workload swap |
| **wiki_operations**     | t60–t69                                                    | WikiArticle.path, WikiArticle.content, access control for wiki CRUD                     |
| **time_tracking**       | t32–t34, t98–t102                                          | TimeEntry.hours, TimeEntry.billable, TimeEntry.status, date ranges                      |
| **comparison**          | t70–t73                                                    | Project count per customer/employee, tie-breaking                                       |
| **location_check**      | t18–t24                                                    | Company.location, Employee.location, multilingual synonyms                              |
| **response_formatting** |                                                            | `outcome`, `links` fields                                                               |

Minimality contract: a rule is **required** only if it enables solving at least one task family. Rules with no task consumer go to `notes`, not to core policy.

## 3. Output: Rule IR Schema

### 3.1 IR types

```
ir_type ∈ {access_control, derive, scale_threshold, enum_definition, field_semantics, lifecycle}
```

### 3.2 IR structure (per rule)

```json
{
  "id": "rule_<family>_<seq>",
  "ir_type": "<ir_type>",
  "entity": "<Entity>",
  "field": "<Entity.field>",
  "predicate": {
    "operator": "allow_if | deny_if | gte | lte | eq | sum_over | enum_in | transition",
    "operands": [
      "..."
    ]
  },
  "covers_tasks": [
    "t17",
    "t56",
    "t86"
  ],
  "source": {
    "page": "hr_skills_and_wills_model.md",
    "anchor": "## Rating scale",
    "quote": "7–8: Strong – recognised expertise / strong motivation."
  },
  "confidence": "high | medium | low",
  "missing_info": null
}
```

### 3.3 Validation invariants

Every emitted rule must satisfy:

1. **Ontology compliance** — `entity` and `field` exist in the schema rail.
2. **Source integrity** — `source.page` exists in wiki; `source.quote` is a substring of the page content under `source.anchor`.
3. **Task coverage** — `covers_tasks` is non-empty (at least one task family needs this rule).
4. **No invention** — every enum value, threshold, or formula must be quote-backed.

Immutability constraint:

- Rule acquisition must not rely on observing mid-task wiki updates. Any wiki update performed as part of a task is treated as a write side-effect and must not
  be assumed to change policy decisions within the same task run.

## 4. Architecture: PolicyAcquisitionAgent on ADK

### 4.1 Framework choice

Built on **ADK Python** (`BaseAgent` subclass), using:

- `Runner` + `InMemorySessionService` for reproducible sessions and rewind.
- Callbacks (`before_model_callback`, `after_model_callback`, `before_tool_callback`, `after_tool_callback`) as mandatory quality gates.
- `RLM` sample pattern for lazy file access and recursive delegation.
- JSONL trajectory logging for traceability.
- ADK `evaluate` layer for regression testing.

### 4.2 Long-context strategy (RLM pattern)

Wiki files are **not** concatenated into a prompt. Instead:

| Layer               | Mechanism                                                               | Purpose                                                       |
|---------------------|-------------------------------------------------------------------------|---------------------------------------------------------------|
| **A — Selection**   | `LazyFileCollection` + metadata index (file list, headings, sizes)      | Address and filter without loading full content               |
| **B — Structuring** | REPL code execution: regex, heading extraction, table parsing           | Convert raw markdown into addressable chunks programmatically |
| **C — Delegation**  | Recursive `rlm_agent(subquery, subcontext)` with batched/parallel calls | Each child reads a small context, returns a compact artifact  |

Concretely:

1. Build a **heading index** across all wiki files (deterministic, no LLM).
2. For each task family, compute a **relevance score** (BM25 over headings + entity/field name overlap).
3. Read only high-scoring sections; expand if coverage is low.
4. Delegate extraction per chunk to child agents; aggregate results.

### 4.3 Pipeline stages

```
IndexAgent → GateAgent → CompileAgent → ValidateAgent → ExportAgent
```

#### Stage 1: IndexAgent (deterministic)

- Input: `LazyFileCollection` of wiki files.
- Output: heading index with `{page, anchor, first_line, signals[]}`.
- Signals detected: `must`, `only`, `forbidden`, `allowed`, `derived`, `defined as`, `threshold`, `status`, `phase`, tables, numeric comparisons (`>=`, `<=`,
  `1–10`).
- No LLM calls.

#### Stage 2: GateAgent (LLM, batched)

- Input: chunk + ontology + signal list.
- Output: candidate statements with source metadata.
- Strict gating rules:
	- Candidate if contains normative signals (see above).
	- Candidate if contains a table where first column resembles enum values.
	- Candidate if contains numbers + comparison operators.
- Output format:

```json
{
  "candidates": [
    {
      "text": "...",
      "source": {
        "page": "...",
        "anchor": "...",
        "quote": "..."
      },
      "hints": {
        "entity": "Project",
        "field": "status"
      }
    }
  ]
}
```

#### Stage 3: CompileAgent (LLM, per candidate)

- Input: one candidate + ontology + allowed IR types.
- Output: one rule IR (see 3.2).
- Closed-world constraint enforced: only ontology symbols allowed; otherwise `missing_info`.
- No free-text in structured fields.

#### Stage 4: ValidateAgent (deterministic)

- Input: compiled rule IR.
- Checks:
	1. JSON Schema conformance of the IR.
	2. `entity` + `field` exist in ontology (schema rail).
	3. `source.page` exists in wiki file list.
	4. `source.quote` is a substring of the actual page content.
	5. Enum values in the rule appear in wiki quotes.
	6. `covers_tasks` is non-empty (task rail).
	7. No conflicting rules for the same field (flag for resolution).
- Failed rules → retry queue (back to CompileAgent with diagnostic).

#### Stage 5: ExportAgent (deterministic)

- Input: validated rule set.
- Output: `policy_rules.json` (core rules) + `policy_notes.json` (non-required / low-confidence).
- Generate coverage report: task family × rule mapping.

### 4.4 ADK callbacks as quality gates

| Callback                | Gate logic                                                                                |
|-------------------------|-------------------------------------------------------------------------------------------|
| `before_model_callback` | Reject any chunk sent to LLM without `source.page` + `source.anchor` attached             |
| `after_model_callback`  | Reject any rule without `source.quote`; reject rules referencing unknown ontology symbols |
| `before_tool_callback`  | Log which wiki files/sections are being read (audit trail)                                |
| `after_tool_callback`   | Log read results hash for reproducibility                                                 |

### 4.5 Session management

- Each pipeline run is a single ADK session via `InMemorySessionService`.
- Session state stores: ontology snapshot, task rail, heading index, candidate queue, compiled rules, validation diagnostics.
- **Rewind** capability: re-run from any stage with modified parameters without re-reading wiki.

Wiki updates during tasks (normative):

- Some benchmark tasks require `update_wiki`.
- Such updates are executed immediately by the validator during plan execution.
- The update must be stored as an entity/event (e.g., `WikiArticle` version in SQL or trace), but it must not retroactively rewrite the policy representation used
  for the current task run.
- A subsequent task run may re-trigger rule acquisition only if `wiki_sha1` indicates the corpus changed.

## 5. Rails specification

### 5.1 Schema/ontology rail

Derived from `policy.py` Pydantic models. Serialized as JSON Schema and injected into every LLM call as a system constraint.

Contents:

- All entity names and their fields with types.
- All enum values (DealPhase, TeamRole, TimeEntryStatus, Outcome, LinkKind, BillableFilter).
- Field-level annotations: `nullable`, `derived_candidate` (e.g., workload is derived from project time slices).
- Synonym dictionary: `{"workload": ["capacity", "utilization", "allocation"], "strong": ["high", "recognised expertise"]}`.

Enforcement: any LLM output referencing a symbol not in this schema is automatically rejected.

### 5.2 Task rail

Derived from `rules/tasks.md`. Structured as:

```yaml
tasks:
  - id: t17
    intent: "Recommend trainer with strong Solventborne formulation and strong Willingness to travel"
    required:
      rule_families: [ scale_threshold, skill_will_query ]
      entities: [ Employee, SkillLevel ]
      fields: [ SkillLevel.level, SkillLevel.name ]
  - id: t4
    intent: "Who has biggest workload in project"
    required:
      rule_families: [ workload_derivation ]
      entities: [ Project, Workload, Employee ]
      fields: [ Workload.time_slice, Project.status ]
  # ... (all 102 tasks classified)
```

Enforcement: after extraction, compute coverage matrix. Any task family with zero covering rules triggers a targeted re-scan of wiki sections with boosted
relevance for that family's entities/fields.

## 6. Metrics

### 6.1 Quality metrics (CI-integrated)

| Metric                  | Definition                                                  | Target |
|-------------------------|-------------------------------------------------------------|--------|
| **Task coverage**       | Fraction of task families with ≥1 covering rule             | 100%   |
| **Ontology compliance** | % of rules passing closed-world check                       | 100%   |
| **Source integrity**    | % of rules where `anchor exists` ∧ `quote substring` passes | 100%   |

### 6.2 Anti-metrics (must minimize)

| Anti-metric    | Definition                                                     |
|----------------|----------------------------------------------------------------|
| **Dead rules** | Rules not covering any task (should be in notes, not core)     |
| **Conflicts**  | Rules for the same entity.field with contradictory definitions |

### 6.3 Evaluation via ADK

Use ADK `evaluate` to compare agent trajectory against golden set:

- Golden rules (manually verified subset).
- Expected coverage per task family.
- Expected source pages per rule family.

## 7. Unknown slot resolution

When CompileAgent returns `missing_info`, the agent must:

1. Create a structured issue: `"Project.status enum values incomplete: found [active, done], missing others?"`.
2. Cite the source: `"wiki/systems_project_registry.md#core-project-fields"`.
3. Attempt self-resolution: scan related wiki sections before escalating.
4. If unresolved: add to `policy_notes.json` with `confidence: low` and the specific missing slot.

## 8. Deliverables

| Artifact                 | Description                                                                |
|--------------------------|----------------------------------------------------------------------------|
| `PolicyAcquisitionAgent` | ADK `BaseAgent` subclass implementing the 5-stage pipeline                 |
| `IndexAgent`             | Deterministic heading/signal indexer                                       |
| `GateAgent`              | LLM-based candidate extractor with strict gating                           |
| `CompileAgent`           | LLM-based IR compiler with closed-world constraint                         |
| `ValidateAgent`          | Deterministic schema + source + coverage validator                         |
| `ExportAgent`            | Deterministic exporter producing `policy_rules.json` + `policy_notes.json` |
| `schema_rail.json`       | Serialized ontology from `policy.py`                                       |
| `task_rail.yaml`         | Classified task list with required rule families                           |
| `policy_rules.json`      | Core validated rule set                                                    |
| `policy_notes.json`      | Non-required / low-confidence observations                                 |
| `coverage_report.json`   | Task family × rule coverage matrix                                         |
| ADK evaluation test set  | Golden rules + expected trajectories for regression                        |

## 9. Acceptance criteria

- **AC-1**: Pipeline produces `policy_rules.json` covering all 10 task families with source-backed rules.
- **AC-2**: Every rule in `policy_rules.json` passes all 4 validation invariants (3.3).
- **AC-3**: No wiki file content is sent to LLM as a monolithic prompt; all access goes through lazy loading + selective reading.
- **AC-4**: Pipeline is reproducible: same wiki input → same rule output (given deterministic seed).
- **AC-5**: ADK callbacks enforce quality gates; no rule reaches export without passing `ValidateAgent`.
- **AC-6**: Coverage report shows 0 dead rules in core set and flags all conflicts.
