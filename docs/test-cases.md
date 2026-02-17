### Case 1 — **t036**: Bulk salary actions based on CEO approval note

**Task**: “Check employees to see if they have an approval note from CEO to raise salary. If so apply it. Employees: BwFV_151, BwFV_152, BwFV_153, BwFV_154”

#### Process B Building execution plan (algorithmic)

- **Trace reference**
	- `docs/t036.json`
- **Step 1: Identity and run context**
	- Call `whoami()`.
	- Treat `whoami()` as the only source of:
		- current user identity
		- department/role context for authorization
		- `today` for any date-dependent logic
- **Step 2: Load each employee by explicit ID**
	- For each employee ID mentioned in the task text, call `employees_get(id=<employee_id>)`.
	- Do not use fuzzy search for these IDs.
- **Step 3: Deterministically detect approval note and parse target salary**
	- Read `employee.notes` from each `employees_get` result.
	- If there is a CEO/exec approval note containing an explicit salary (trace example: “... increase salary to 105000”), parse that integer as
	  `target_salary`.
	- If no parseable approval exists, mark employee as “no action”.
- **Step 4: Apply the pre-approved salary change (write)**
	- For each employee with a parsed `target_salary`, call `employee_update_safe(employee=<id>, salary=<target_salary>)`.
	- Use the tool output as immediate confirmation that the salary is now the target value.
- **Step 5: Respond**
	- Call `respond(outcome='ok_answer')` with a per-employee summary.
	- Links should match the trace behavior: include only the employee(s) whose salary was actually updated (in the trace: `BwFV_154`).

#### Process C validation / proof checklist

- **C0. Trace integrity**
	- Trace contains exactly:
		- 1 `whoami`
		- 4 `employees_get` calls (one per listed employee)
		- 0..4 `employee_update_safe` calls
		- 1 `respond`
- **C1. Authorization proof**
	- Proof inputs: `whoami.department`, `whoami.current_user`, `whoami.is_public`.
	- Proof obligation: salary write is permitted for the actor.
- **C2. Employee evidence binding**
	- For each requested employee ID `E`, there is a corresponding `employees_get(id=E)`.
	- Each returned payload must satisfy `employee.id == E`.
- **C3. Approval-note parsing proof**
	- For each employee `E`, the validator derives:
		- `approval_detected(E)` from `employee.notes`
		- if detected, `target_salary(E)` from `employee.notes`
	- If `employee_update_safe(employee=E, salary=S)` appears in trace, then `target_salary(E) == S` must hold.
- **C4. Write postcondition proof**
	- For each `employee_update_safe(employee=E, salary=S)` call, the tool output must include `employee.salary == S`.
- **C5. Response contract + links grounding**
	- `respond.outcome == 'ok_answer'`.
	- Every link is grounded in an entity returned by tool calls.
	- Links reflect actual updates (trace: only `BwFV_154`).

---

### Case 2 — **t092**: Swap roles AND workloads for two people on a project (team mutation)

**Task**: “Adjust internal debottlenecking initiative for the Serbian production plant and swap roles AND workloads of Marina Vukalović and Rossi Luca (fix
earlier entry mistake).”

#### Process B Building execution plan (algorithmic)

- **Trace reference**
	- `docs/t092.json`
- **Step 1: Identity and run context**
	- Call `whoami()`.
- **Step 2: Resolve the project by paraphrase**
	- Call `projects_search(query=..., limit=5, offset=0)`.
	- Trace-aligned retry:
		- first query may return no results
		- retry with broader query to find `proj_ops_serbia_debottlenecking_bellini`
	- If multiple projects match, stop with `respond(outcome='none_clarification_needed')`.
- **Step 3: Resolve employees by name (with name-order fallback)**
	- Call `employees_search(query=..., limit=5, offset=0)`.
	- If “Rossi Luca” returns no results, retry with “Luca Rossi”.
- **Step 4: Load current team and compute swap**
	- Call `projects_get(id=<project_id>)` and load `project.team`.
	- Locate both employees in the team.
	- Swap both fields:
		- `role`
		- `time_slice`
	- Preserve all other team entries unchanged.
- **Step 5: Write (replace) + verify**
	- Call `projects_team_update(id=<project_id>, team=<full team array>)`.
	- Call `projects_get(id=<project_id>)` again to verify the swap persisted.
- **Step 6: Respond**
	- Call `respond(outcome='ok_answer')`.
	- Links should match the trace behavior: project + both employees.

#### Process C validation / proof checklist

- **C0. Trace integrity**
	- Trace contains:
		- `whoami`
		- 1..N `projects_search` calls with `limit=5, offset=0`
		- 1..M `employees_search` calls with `limit=5, offset=0`
		- `projects_get` (pre)
		- `projects_team_update`
		- `projects_get` (post)
		- `respond`
- **C1. Project and employee identity proofs**
	- Chosen `project_id` appears in `projects_search` output and is `found=true` in `projects_get`.
	- Each chosen target employee ID appears in `employees_search` output.
	- Both target employee IDs exist in the pre-state `projects_get(...).project.team`.
- **C2. Swap correctness proof**
	- Pre-state extracts `{role,time_slice}` for both employees.
	- Post-state must show the two entries swapped exactly, and all other team entries unchanged.
- **C3. Response contract + links grounding**
	- `respond.outcome == 'ok_answer'`.
	- Links contain exactly the project plus the two swapped employees.

---

### Case 3 — **t101**: Void an incorrect time entry and create a new corrected entry

**Task**: “I accidentally logged 8 hours on Ramp repair and recoating programme on 2025-05-10, but I only worked 6. Please void that time entry and create new
copy with 8 hours.”

This is complex because:

- it’s a write + requires finding the exact entry
- involves lifecycle/status rules
- the instruction includes an apparent contradiction that patch evolution explicitly says: **execute literally as asked**

#### Process B Building execution plan (algorithmic)

- **Trace reference**
	- `docs/t101.json`
- **Step 1: Identity and run context**
	- Call `whoami()` and set `actor_employee_id = whoami.current_user`.
- **Step 2: Resolve the project by name**
	- Call `projects_search(query='Ramp repair and recoating programme', limit=5, offset=0)`.
	- If multiple projects match, stop with `respond(outcome='none_clarification_needed')`.
- **Step 3: Find the exact entry to void (same employee + exact date)**
	- Call `time_search(employee=<actor_employee_id>, date_from='2025-05-10', date_to='2025-05-10', limit=5, offset=0)`.
	- Select the entry where `project == <resolved_project_id>` and `hours == 8`.
	- If multiple entries still match, stop with `respond(outcome='none_clarification_needed')` asking which entry ID to void.
- **Step 4: Void + create replacement (execute literally as requested)**
	- Call `time_update(id=<entry_id>, status='voided')`.
	- Call
	  `time_log(employee=<actor_employee_id>, project=<resolved_project_id>, date='2025-05-10', hours=8, billable=true, work_category='customer_project', status='draft')`.
- **Step 5: Respond**
	- Call `respond(outcome='ok_answer')`.
	- Links should match the trace behavior: project + customer.

#### Process C validation / proof checklist

- **C0. Trace integrity**
	- Trace contains:
		- `whoami`
		- `projects_search(limit=5, offset=0)`
		- `time_search(limit=5, offset=0)`
		- `time_update`
		- `time_log`
		- `respond`
- **C1. Identity + permission proof**
	- Actor ID used in `time_search` and `time_log` equals `whoami.current_user`.
- **C2. Project binding proof**
	- `projects_search` yields the `project_id` used later in `time_log`.
- **C3. Entry selection proof**
	- `time_update.id` is an element of the `time_search.entries[*].id` list.
	- If more than one matching candidate exists, validator requires clarification instead of guessing.
- **C4. Mutation correctness proof**
	- `time_update.status == 'voided'`.
	- `time_log` includes required fields and uses:
		- `work_category='customer_project'`
		- `status='draft'`
		- `hours == 8` (as requested)
- **C5. Response contract + links grounding**
	- `respond.outcome == 'ok_answer'`.
	- Links include the project and customer referenced by the updated/created entries.

---

### Case 4 — **t068**: Create wiki pages for every customer (bulk wiki writes)

**Task**: “Create wiki pages customers/CUSTOMER_ID.md with content 'PLACEHOLDER' (no newline) for every customer”

#### Process B Building execution plan (algorithmic)

- **Trace reference**
	- `docs/t068.json`
- **Step 1: Identity and run context**
	- Call `whoami()`.
- **Step 2: Enumerate customers via paging (`limit=5`)**
	- Call `customers_list(limit=5, offset=0)`.
	- While `next_offset != -1`, call `customers_list(limit=5, offset=<next_offset>)`.
- **Step 3: Create/update wiki page for each customer**
	- For each discovered customer id `cust_id`, call:
		- `wiki_update(file=f'customers/{cust_id}.md', content='PLACEHOLDER')`
	- Content must be exactly `PLACEHOLDER` (no newline).
- **Step 4: Respond**
	- Call `respond(outcome='ok_answer')` and list all created paths.
	- Links should match the trace behavior: one `wiki` link per created page.

#### Process C validation / proof checklist

- **C0. Trace integrity**
	- Trace contains:
		- `whoami`
		- N>=1 `customers_list(limit=5, offset=...)` calls until `next_offset == -1`
		- exactly one `wiki_update` call per discovered customer id
		- `respond`
- **C1. Paging proof**
	- Each `customers_list` call uses `limit=5`.
	- Offsets must follow the previous call’s `next_offset`.
- **C2. Write-set proof (customers ↔ wiki pages)**
	- For every customer id `cust_id` returned by paging, there is a `wiki_update(file=f'customers/{cust_id}.md')` call.
	- No `wiki_update` writes occur outside the `customers/` prefix.
	- Each `wiki_update.content == 'PLACEHOLDER'` exactly.
- **C3. Response contract + links grounding**
	- `respond.outcome == 'ok_answer'`.
	- Every `wiki` link corresponds to a file that was written via `wiki_update`.

---

### Case 5 — **t077**: Coaching recommendation (multi-skill coaching, +2 levels rule)

**Task**: “I want to upskill an employee. Get me a list of employees, that can coach Richter Charlotte on his skills to improve them further.”

This is complex because it requires:

- robust person resolution
- multi-skill comparison logic
- ranking with ties
- strict inclusion/exclusion rules

#### Process B Building execution plan (algorithmic)

- **Trace reference**
	- `docs/t077.json`
- **Step 1: Identity and run context**
	- Call `whoami()`.
- **Step 2: Resolve the target employee (name-order fallback)**
	- Call `employees_search(query='Richter Charlotte', limit=5, offset=0)`.
	- If empty, retry: `employees_search(query='Charlotte Richter', limit=5, offset=0)`.
	- If multiple matches, stop with `respond(outcome='none_clarification_needed')`.
- **Step 3: Load target profile**
	- Call `employees_get(id=<target_employee_id>)` and extract the `skills` list.
- **Step 4: Derive coaching requirements (+2 levels, cap at 10)**
	- For each target skill `(name, level)`, compute `required_level = min(level + 2, 10)`.
- **Step 5: Find coaches in one deterministic step**
	- Call `find_employees_by_skill(skills=[{name, min_level: required_level}...], exclude_employee_id=<target_employee_id>, top_n=50)`.
	- Trace example outcome:
		- `total_coaches=44`
- **Step 6: Respond**
	- Call `respond(outcome='ok_answer')`.
	- Links should match the trace behavior: one `employee` link per coach returned (44 total).

#### Process C validation / proof checklist

- **C0. Trace integrity**
	- Trace contains:
		- `whoami`
		- 1..2 `employees_search(limit=5, offset=0)` calls
		- `employees_get`
		- `find_employees_by_skill`
		- `respond`
- **C1. Target employee binding proof**
	- The target employee id used in `employees_get` appears in the successful `employees_search` output.
- **C2. Requirement derivation proof (+2 rule)**
	- The `find_employees_by_skill.skills[]` input is deterministically derived from the target’s `employees_get(...).employee.skills` list.
	- For each required entry:
		- `min_level == min(target_level + 2, 10)`.
- **C3. Coach-set binding proof**
	- Every `respond.links[*].id` is an employee id present in `find_employees_by_skill` output.
	- The count of employee links equals `find_employees_by_skill.total_coaches` (trace: 44).
- **C4. Exclusion proof**
	- `exclude_employee_id == target_employee_id`.
	- Target employee id is not present in response links.
- **C5. Response contract proof**
	- `respond.outcome == 'ok_answer'`.