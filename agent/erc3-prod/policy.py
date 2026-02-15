"""AgenticSolver local policy/domain schema.

This module mirrors the *major* ERC3 API entities (see `erc3.erc3.dtos`) as local
Pydantic models with explicit descriptions. The intent is to provide a stable,
typed substrate for:
- Local constrained validation
- SQL persistence and joins
- Response validation (outcome + links)
"""

from __future__ import annotations

from typing import List, Literal, Optional, TypeAlias

from pydantic import BaseModel, Field

# ============================================================
# Core type aliases (IDs)
# ============================================================

EmployeeID: TypeAlias = str
CompanyID: TypeAlias = str
ProjectID: TypeAlias = str
TimeEntryID: TypeAlias = str

# ============================================================
# Core enums (Literal-based for zero-dependency portability)
# ============================================================

Outcome: TypeAlias = Literal[
    "ok_answer",
    "ok_not_found",
    "denied_security",
    "none_clarification_needed",
    "none_unsupported",
    "error_internal",
]

LinkKind: TypeAlias = Literal["employee", "customer", "project", "wiki", "location"]
DealPhase: TypeAlias = Literal["idea", "exploring", "active", "paused", "archived"]
TeamRole: TypeAlias = Literal["Lead", "Engineer", "Designer", "QA", "Ops", "Other"]
TimeEntryStatus: TypeAlias = Literal["", "draft", "submitted", "approved", "invoiced", "voided"]
BillableFilter: TypeAlias = Literal["", "billable", "non_billable"]
TaskStatus: TypeAlias = Literal["new", "in_progress", "completed", "failed"]


# ============================================================
# Response links (benchmark-facing)
# ============================================================


class AgentLink(BaseModel):
    """A typed link to an entity in the underlying systems."""

    kind: LinkKind = Field(..., description="Entity kind: employee/customer/project/wiki/location")
    id: str = Field(..., description="Entity identifier (ID for registries, or path for wiki)")


class Response(BaseModel):
    """Agent response payload for `/respond` (pre-validation representation)."""

    message: str = Field(..., description="Human-readable response message")
    outcome: Outcome = Field(..., description="Outcome code describing result category")
    links: List[AgentLink] = Field(
        default_factory=list,
        description="Optional typed links to referenced entities (defaults to empty list)",
    )


class Task(BaseModel):
    """Benchmark task metadata (mirrors `erc3.core.TaskInfo`)."""

    spec_id: str = Field(..., description="Task spec identifier")
    task_id: str = Field(..., description="Unique task identifier")
    num: int = Field(..., description="Task number within the benchmark")
    task_text: str = Field(..., description="Natural-language task prompt")
    status: TaskStatus = Field(..., description="Task lifecycle status")
    benchmark: str = Field(..., description="Benchmark name, e.g. erc3-prod")
    score: float = Field(..., description="Current score for this task")
    error_message: Optional[str] = Field(None, description="Error message, if task failed")


# ============================================================
# HR: skills & wills
# ============================================================


class SkillLevel(BaseModel):
    """A single skill/will entry with a 1–10 level scale."""

    name: str = Field(..., description="Skill or will name (canonical string)")
    level: int = Field(..., description="Level on a 1–10 scale")


class SkillFilter(BaseModel):
    """Filter for searching employees by skill/will level ranges."""

    name: str = Field(..., description="Skill or will name")
    min_level: int = Field(..., description="Minimum required level")
    max_level: int = Field(0, description="Optional maximum level (0 means unbounded)")


# ============================================================
# Employee Registry
# ============================================================


class Employee(BaseModel):
    """Employee entity used across list/search/get/update contexts."""

    id: EmployeeID = Field(..., description="Internal employee identifier")
    name: str = Field(..., description="Full name")
    email: str = Field(..., description="Auto-generated work email")
    salary: int = Field(..., description="Exact salary (confidential; visibility depends on permissions)")
    location: str = Field(..., description="Employee location/site")
    department: str = Field(..., description="Employee home department")
    notes: Optional[str] = Field(None, description="Free-text HR/internal notes")
    skills: List[SkillLevel] = Field(default_factory=list, description="List of skills")
    wills: List[SkillLevel] = Field(default_factory=list, description="List of wills/motivations")
    time_entries: List[TimeEntry] = Field(
        default_factory=list,
        description="Prefetched time entries for this employee",
    )
    time_summaries: List[TimeSummary] = Field(
        default_factory=list,
        description="Prefetched time summaries for this employee (GreedyErc3Client)",
    )

    def get_time_summary_by_employee(self) -> List[TimeSummary]:
        return list(self.time_summaries)


class UserContext(BaseModel):
    """Caller identity and environment context returned by `who_am_i()`."""

    current_user: Optional[EmployeeID] = Field(None, description="Employee ID of current caller, if authenticated")
    is_public: bool = Field(..., description="True for public/unauthenticated mode")
    location: Optional[str] = Field(None, description="Caller location, if known")
    department: Optional[str] = Field(None, description="Caller department, if known")
    today: Optional[str] = Field(None, description="Current date as provided by the system")
    wiki_sha1: Optional[str] = Field(None, description="Current wiki digest hash")
    time_summaries_by_employee: List[TimeSummary] = Field(None, description="Time summaries by employee")
    time_summaries_by_project: List[TimeSummary] = Field(None, description="Time summaries by project")
    time_entries: List[TimeEntry] = Field(None, description="Time entries for the current run")

    employees: List[Employee] = Field(
        default_factory=list,
        description="Prefetched employees for the current run",
    )
    customers: List[Company] = Field(
        default_factory=list,
        description="Prefetched customers for the current run",
    )
    projects: List[Project] = Field(
        default_factory=list,
        description="Prefetched projects for the current run",
    )

    def get_employees(self) -> List[Employee]:
        return list(self.employees)

    def get_customers(self) -> List[Company]:
        return list(self.customers)

    def get_projects(self) -> List[Project]:
        return list(self.projects)


# ============================================================
# CRM: Customers / Companies
# ============================================================


class Company(BaseModel):
    """Customer/company entity used across list/search/get contexts."""

    id: CompanyID = Field(..., description="Internal customer identifier")
    name: str = Field(..., description="Customer legal/name")
    location: str = Field(..., description="Primary customer location/country tag")
    deal_phase: DealPhase = Field(..., description="Deal phase (idea/exploring/active/paused/archived)")
    high_level_status: str = Field(..., description="High-level relationship status")
    brief: Optional[str] = Field(None, description="Short descriptive brief")
    primary_contact_name: Optional[str] = Field(None, description="Primary customer contact name")
    primary_contact_email: Optional[str] = Field(None, description="Primary customer contact email")
    account_manager: Optional[EmployeeID] = Field(None, description="Employee ID of assigned account manager")
    projects: List[Project] = Field(
        default_factory=list,
        description="Projects linked to this customer (GreedyErc3Client)",
    )
    time_entries: List[TimeEntry] = Field(
        default_factory=list,
        description="Prefetched time entries linked to this customer",
    )


# ============================================================
# Project Registry
# ============================================================


class Workload(BaseModel):
    """Project team entry: employee allocation as an FTE time-slice."""

    employee: EmployeeID = Field(..., description="Employee ID")
    time_slice: float = Field(..., description="Fraction of an FTE allocated to the project")
    role: TeamRole = Field(..., description="Role of the employee in the project team")


class Project(BaseModel):
    """Project entity used across list/search/get contexts."""

    id: ProjectID = Field(..., description="Internal project identifier")
    name: str = Field(..., description="Project name")
    customer: CompanyID = Field(..., description="Linked customer ID")
    status: DealPhase = Field(..., description="Project status aligned with deal phases")
    description: Optional[str] = Field(None, description="Project brief/description")
    team: List[Workload] = Field(default_factory=list, description="Project team allocations")
    customers: List[Company] = Field(
        default_factory=list,
        description="Customer objects referenced by this project (GreedyErc3Client)",
    )
    time_entries: List[TimeEntry] = Field(
        default_factory=list,
        description="Prefetched time entries linked to this project (GreedyErc3Client)",
    )
    time_summaries: List[TimeSummary] = Field(
        default_factory=list,
        description="Prefetched time summaries for this project (GreedyErc3Client)",
    )

    def get_time_summary_by_project(self) -> List[TimeSummary]:
        return list(self.time_summaries)


# ============================================================
# Wiki
# ============================================================


class WikiArticle(BaseModel):
    """A wiki page as a (path, content) pair."""

    path: str = Field(..., description="Wiki path, e.g. systems/project_registry.md")
    content: str = Field(..., description="Full markdown content")


class WikiSearchSnippet(BaseModel):
    """A snippet returned by wiki search."""

    content: str = Field(..., description="Snippet content")
    linum: int = Field(..., description="1-based line number")
    path: str = Field(..., description="Wiki page path")


# ============================================================
# Time Tracking
# ============================================================


class TimeEntry(BaseModel):
    """A time entry used for logging and update payloads.
    It's also Request DTO for updating an existing time entry (mirrors `/time/update`)
    """

    id: Optional[TimeEntryID] = Field(description="Internal time entry identifier")
    employee: Optional[EmployeeID] = Field(description="Employee the time is logged for")
    customer: Optional[CompanyID] = Field(None, description="Optional customer ID (often derived from project)")
    project: Optional[ProjectID] = Field(None, description="Optional project ID (customer or internal)")
    date: str = Field(..., description="Date in YYYY-MM-DD")
    hours: float = Field(..., description="Hours as a decimal number")
    work_category: str = Field(..., description="Work category tag")
    notes: str = Field(..., description="Short free-text notes")
    billable: bool = Field(..., description="Billable vs non-billable flag")
    status: TimeEntryStatus = Field(..., description="Time entry workflow status")
    logged_by: Optional[EmployeeID] = Field(description="Employee who performed the logging")
    changed_by: EmployeeID = Field(description="Employee who performed the update")


class TimeEntriesRequest(BaseModel):
    """Request DTO for searching time entries (mirrors `/time/search`)."""

    employee: Optional[EmployeeID] = Field(None, description="Filter by employee ID")
    customer: Optional[CompanyID] = Field(None, description="Filter by customer ID")
    project: Optional[ProjectID] = Field(None, description="Filter by project ID")
    date_from: Optional[str] = Field(None, description="Start date (YYYY-MM-DD)")
    date_to: Optional[str] = Field(None, description="End date (YYYY-MM-DD)")
    work_category: Optional[str] = Field(None, description="Work category filter")
    billable: BillableFilter = Field("billable", description="Billable filter: billable/non_billable")
    status: TimeEntryStatus = Field("", description="Time entry status filter")


class TimeEntries(BaseModel):
    """Response DTO for searching time entries (mirrors `/time/search`)."""

    entries: List[TimeEntry] = Field(default_factory=list, description="Matching time entries")
    next_offset: Optional[int] = Field(None, description="Offset for the next page, if any")
    total_hours: float = Field(..., description="Total hours across all matches")
    total_billable: float = Field(..., description="Total billable hours across all matches")
    total_non_billable: float = Field(..., description="Total non-billable hours across all matches")


class TimeSummary(BaseModel):
    """Aggregated time summary grouped by project/employee/customer."""

    employee: EmployeeID = Field(..., description="Employee ID")
    customer: CompanyID = Field(..., description="Customer ID")
    project: ProjectID = Field(..., description="Project ID")
    total_hours: float = Field(..., description="Total hours in the requested date range")
    billable_hours: float = Field(..., description="Billable hours")
    non_billable_hours: float = Field(..., description="Non-billable hours")
    distinct_employees: int = Field(..., description="Number of distinct employees who logged time")
