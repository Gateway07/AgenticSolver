from __future__ import annotations

from typing import Any, Dict, Generic, List, Optional, Type, TypeVar

from erc3.erc3.client import Erc3Client
from pydantic import BaseModel, Field

from policy import (
    AgentLink,
    BillableFilter,
    Company,
    DealPhase,
    Employee,
    EmployeeID,
    Outcome,
    Project,
    ProjectID,
    SkillFilter,
    SkillLevel,
    TimeEntryID,
    WikiArticle,
    WikiSearchSnippet,
    UserContext,
    TimeSummary,
    TimeEntry,
    TimeEntriesRequest,
    TimeEntries,
)

TModel = TypeVar("TModel", bound=BaseModel)


class PagedResult(BaseModel, Generic[TModel]):
    items: List[TModel] = Field(default_factory=list, description="Page items")
    next_offset: Optional[int] = Field(None, description="Offset for the next page, if any")


class WikiListResult(BaseModel):
    paths: List[str] = Field(default_factory=list, description="Wiki page paths")
    sha1: str = Field(..., description="Wiki digest hash")


def _to_dict(obj: Any) -> Dict[str, Any]:
    if obj is None:
        return {}
    if isinstance(obj, dict):
        return obj  # type: ignore[return-value]
    model_dump = getattr(obj, "model_dump", None)
    if callable(model_dump):
        return model_dump()  # type: ignore[return-value]
    to_dict = getattr(obj, "dict", None)
    if callable(to_dict):
        return to_dict()  # type: ignore[return-value]
    raise TypeError(f"Unsupported DTO object type: {type(obj).__name__}")


def _model_from(model_cls: Type[TModel], dto_obj: Any) -> TModel:
    payload = _to_dict(dto_obj)
    model_validate = getattr(model_cls, "model_validate", None)
    if callable(model_validate):
        return model_validate(payload)
    return model_cls.parse_obj(payload)  # pydantic v1


class PrimitiveErc3APIClient:
    """Typed wrappers over `erc3.erc3.client.Erc3Client`.

    This layer is intentionally thin and deterministic:
    - It does not implement business logic.
    - It normalizes DTOs into local `policy.py` entities for downstream validation/SQL.
    """

    def __init__(self, base_url: str):
        self._client = Erc3Client(base_url=base_url)

    # -----------------------------
    # Core
    # -----------------------------

    def who_am_i(self) -> UserContext:
        resp = self._client.who_am_i()
        return _model_from(UserContext, resp)

    def provide_agent_response(
            self, message: str, outcome: Outcome, links: Optional[List[AgentLink]] = None
    ) -> None:
        self._client.provide_agent_response(message=message, outcome=outcome, links=links or [])

    # -----------------------------
    # Employees
    # -----------------------------

    def list_employees(self, offset: int, limit: int) -> PagedResult[Employee]:
        resp = self._client.list_employees(offset=offset, limit=limit)
        employees = [_model_from(Employee, e) for e in (resp.employees or [])]
        return PagedResult[Employee](items=employees, next_offset=resp.next_offset)

    def search_employees(
            self,
            offset: int,
            limit: int,
            query: Optional[str] = None,
            location: Optional[str] = None,
            department: Optional[str] = None,
            manager: Optional[str] = None,
            skills: Optional[List[SkillFilter]] = None,
            wills: Optional[List[SkillFilter]] = None,
    ) -> PagedResult[Employee]:
        resp = self._client.search_employees(
            offset=offset,
            limit=limit,
            query=query,
            location=location,
            department=department,
            manager=manager,
            skills=[_to_dict(s) for s in (skills or [])],
            wills=[_to_dict(w) for w in (wills or [])],
        )
        employees = [_model_from(Employee, e) for e in (resp.employees or [])]
        return PagedResult[Employee](items=employees, next_offset=resp.next_offset)

    def get_employee(self, employee_id: EmployeeID) -> Optional[Employee]:
        resp = self._client.get_employee(employee_id)
        if resp.employee is None:
            return None
        return _model_from(Employee, resp.employee)

    def update_employee_info(
            self,
            employee: EmployeeID,
            notes: Optional[str] = None,
            salary: Optional[int] = None,
            skills: Optional[List[SkillLevel]] = None,
            wills: Optional[List[SkillLevel]] = None,
            location: Optional[str] = None,
            department: Optional[str] = None,
            changed_by: Optional[EmployeeID] = None,
    ) -> Optional[Employee]:
        resp = self._client.update_employee_info(
            employee=employee,
            notes=notes,
            salary=salary,
            skills=[_to_dict(s) for s in (skills or [])],
            wills=[_to_dict(w) for w in (wills or [])],
            location=location,
            department=department,
            changed_by=changed_by,
        )
        if resp.employee is None:
            return None
        return _model_from(Employee, resp.employee)

    # -----------------------------
    # Wiki
    # -----------------------------

    def list_wiki(self) -> WikiListResult:
        resp = self._client.list_wiki()
        return WikiListResult(paths=list(resp.paths or []), sha1=resp.sha1)

    def load_wiki(self, file: str) -> WikiArticle:
        resp = self._client.load_wiki(file=file)
        return WikiArticle(path=resp.file, content=resp.content)

    def search_wiki(self, query_regex: str) -> List[WikiSearchSnippet]:
        resp = self._client.search_wiki(query_regex=query_regex)
        return [_model_from(WikiSearchSnippet, r) for r in (resp.results or [])]

    def update_wiki(
            self,
            file: str,
            content: str,
            changed_by: Optional[EmployeeID] = None,
    ) -> None:
        self._client.update_wiki(file=file, content=content, changed_by=changed_by)

    # -----------------------------
    # Customers
    # -----------------------------

    def list_customers(self, offset: int, limit: int) -> PagedResult[Company]:
        resp = self._client.list_customers(offset=offset, limit=limit)
        companies = [_model_from(Company, c) for c in (resp.companies or [])]
        return PagedResult[Company](items=companies, next_offset=resp.next_offset)

    def search_customers(
            self,
            offset: int,
            limit: int,
            query: Optional[str] = None,
            deal_phase: Optional[List[DealPhase]] = None,
            account_managers: Optional[List[EmployeeID]] = None,
            locations: Optional[List[str]] = None,
    ) -> PagedResult[Company]:
        resp = self._client.search_customers(
            offset=offset,
            limit=limit,
            query=query,
            deal_phase=deal_phase or [],
            account_managers=account_managers or [],
            locations=locations or [],
        )
        companies = [_model_from(Company, c) for c in (resp.companies or [])]
        return PagedResult[Company](items=companies, next_offset=resp.next_offset)

    def get_customer(self, customer_id: str) -> Optional[Company]:
        resp = self._client.get_customer(customer_id)
        if not resp.found or resp.company is None:
            return None
        return _model_from(Company, resp.company)

    # -----------------------------
    # Projects
    # -----------------------------

    def list_projects(self, offset: int, limit: int) -> PagedResult[Project]:
        resp = self._client.list_projects(offset=offset, limit=limit)
        projects = [_model_from(Project, p) for p in (resp.projects or [])]
        return PagedResult[Project](items=projects, next_offset=resp.next_offset)

    def search_projects(
            self,
            offset: int,
            limit: int,
            query: Optional[str] = None,
            customer_id: Optional[str] = None,
            status: Optional[List[DealPhase]] = None,
            team: Optional[Dict[str, Any]] = None,
            include_archived: bool = False,
    ) -> PagedResult[Project]:
        resp = self._client.search_projects(
            offset=offset,
            limit=limit,
            query=query,
            customer_id=customer_id,
            status=status or [],
            team=team,
            include_archived=include_archived,
        )
        projects = [_model_from(Project, p) for p in (resp.projects or [])]
        return PagedResult[Project](items=projects, next_offset=resp.next_offset)

    def get_project(self, project_id: ProjectID) -> Optional[Project]:
        resp = self._client.get_project(project_id)
        if not resp.found or resp.project is None:
            return None
        return _model_from(Project, resp.project)

    def update_project_team(
            self, project_id: ProjectID, team: List[Dict[str, Any]], changed_by: Optional[EmployeeID] = None
    ) -> None:
        self._client.update_project_team(project_id=project_id, team=team, changed_by=changed_by)

    def update_project_status(
            self, project_id: ProjectID, status: DealPhase, changed_by: Optional[EmployeeID] = None
    ) -> None:
        self._client.update_project_status(project_id=project_id, status=status, changed_by=changed_by)

    # -----------------------------
    # Time tracking
    # -----------------------------

    def log_time_entry(self, request: TimeEntry) -> TimeEntry:
        model_dump = getattr(request, "model_dump", None)
        if callable(model_dump):
            request_kwargs = model_dump(exclude_none=True)
        else:
            request_kwargs = request.dict(exclude_none=True)

        resp = self._client.log_time_entry(**request_kwargs)
        return _model_from(TimeEntry, resp)

    def update_time_entry(self, request: TimeEntry) -> None:
        model_dump = getattr(request, "model_dump", None)
        if callable(model_dump):
            request_kwargs = model_dump(exclude_none=True)
        else:
            request_kwargs = request.dict(exclude_none=True)

        self._client.update_time_entry(**request_kwargs)

    def get_time_entry(self, entry_id: TimeEntryID) -> Optional[TimeEntry]:
        resp = self._client.get_time_entry(entry_id)
        if resp.entry is None:
            return None
        payload = _to_dict(resp.entry)
        payload["id"] = entry_id
        return _model_from(TimeEntry, payload)

    def search_time_entries(self, limit: int, offset: int, request: TimeEntriesRequest) -> TimeEntries:
        model_dump = getattr(request, "model_dump", None)
        if callable(model_dump):
            request_kwargs = model_dump(exclude_none=True)
        else:
            request_kwargs = request.dict(exclude_none=True)

        request_kwargs["limit"] = limit
        request_kwargs["offset"] = offset

        resp = self._client.search_time_entries(**request_kwargs)
        entries = [_model_from(TimeEntry, e) for e in (resp.entries or [])]
        return TimeEntries(
            entries=entries,
            next_offset=resp.next_offset,
            total_hours=resp.total_hours,
            total_billable=resp.total_billable,
            total_non_billable=resp.total_non_billable,
        )

    def time_summary_by_project(
            self,
            date_from: str,
            date_to: str,
            customers: Optional[List[str]] = None,
            projects: Optional[List[str]] = None,
            employees: Optional[List[str]] = None,
            billable: BillableFilter = "",
    ) -> List[TimeSummary]:
        resp = self._client.time_summary_by_project(
            date_from=date_from,
            date_to=date_to,
            customers=customers or [],
            projects=projects or [],
            employees=employees or [],
            billable=billable,
        )
        return [_model_from(TimeSummary, s) for s in (resp.summaries or [])]

    def time_summary_by_employee(
            self,
            date_from: str,
            date_to: str,
            customers: Optional[List[str]] = None,
            projects: Optional[List[str]] = None,
            employees: Optional[List[str]] = None,
            billable: BillableFilter = "",
    ) -> List[TimeSummary]:
        resp = self._client.time_summary_by_employee(
            date_from=date_from,
            date_to=date_to,
            customers=customers or [],
            projects=projects or [],
            employees=employees or [],
            billable=billable,
        )
        return [_model_from(TimeSummary, s) for s in (resp.summaries or [])]


class MemoryErc3Client(PrimitiveErc3APIClient):
    """Greedy prefetch client built on top of PrimitiveErc3APIClient.

    Design goals:
    - Prefetch core registries (employees/customers/projects) during __init__ via paging.
    - Prefetch user context (`who_am_i`) first, and expose it as a cached attribute.
    - Prefetch time summaries during __init__ for a deterministic date range.

    Notes:
    - Time summaries require a date range. This class makes `date_from`/`date_to` mandatory
      to avoid guessing and to keep runs reproducible.
    """

    def __init__(self, base_url: str, date_from: str, date_to: str):
        super().__init__(base_url=base_url)
        self.page_limit = 999

        self.user_context: UserContext = self.who_am_i()

        self.user_context.employees = self._fetch_all_employees()
        self.user_context.customers = self._fetch_all_customers()
        self.user_context.projects = self._fetch_all_projects()
        self.user_context.time_entries = self._fetch_all_time_entries(date_from=date_from, date_to=date_to)

        self._populate_references()

        self.user_context.time_summaries_by_project = self.time_summary_by_project(
            date_from=date_from,
            date_to=date_to,
            customers=[],
            projects=[],
            employees=[],
            billable="",
        )
        self.user_context.time_summaries_by_employee = self.time_summary_by_employee(
            date_from=date_from,
            date_to=date_to,
            customers=[],
            projects=[],
            employees=[],
            billable="",
        )

        self._populate_time_summaries()

    def _fetch_all_employees(self) -> List[Employee]:
        results: List[Employee] = []
        offset: int = 0
        while True:
            page = self.list_employees(offset=offset, limit=self.page_limit)
            results.extend(page.items)
            if page.next_offset is None:
                break
            offset = page.next_offset
        return results

    def _fetch_all_customers(self) -> List[Company]:
        results: List[Company] = []
        offset: int = 0
        while True:
            page = self.list_customers(offset=offset, limit=self.page_limit)
            results.extend(page.items)
            if page.next_offset is None:
                break
            offset = page.next_offset
        return results

    def _fetch_all_projects(self) -> List[Project]:
        results: List[Project] = []
        offset: int = 0
        while True:
            page = self.list_projects(offset=offset, limit=self.page_limit)
            results.extend(page.items)
            if page.next_offset is None:
                break
            offset = page.next_offset
        return results

    def _fetch_all_time_entries(self, *, date_from: str, date_to: str) -> List[TimeEntry]:
        results: List[TimeEntry] = []
        offset: int = 0

        request = TimeEntriesRequest(
            date_from=date_from,
            date_to=date_to,
            employee=None,
            customer=None,
            project=None,
            work_category=None,
            billable="",
            status="",
        )

        while True:
            page = self.search_time_entries(limit=self.page_limit, offset=offset, request=request)
            results.extend(page.entries)
            if page.next_offset is None:
                break
            offset = page.next_offset

        return results

    def _populate_references(self) -> None:
        customers_by_id: Dict[str, Company] = {c.id: c for c in self.user_context.customers}
        projects_by_id: Dict[str, Project] = {p.id: p for p in self.user_context.projects}
        employees_by_id: Dict[str, Employee] = {e.id: e for e in self.user_context.employees}

        for project in self.user_context.projects:
            customer = customers_by_id.get(project.customer)
            if customer is None:
                continue

            project.customers.append(customer)
            customer.projects.append(project)

        for time_entry in self.user_context.time_entries:
            if time_entry.employee is not None:
                employee = employees_by_id.get(str(time_entry.employee))
                if employee is not None:
                    employee.time_entries.append(time_entry)

            if time_entry.customer is not None:
                customer = customers_by_id.get(str(time_entry.customer))
                if customer is not None:
                    customer.time_entries.append(time_entry)

            if time_entry.project is not None:
                project = projects_by_id.get(time_entry.project)
                if project is not None:
                    project.time_entries.append(time_entry)

    def _populate_time_summaries(self) -> None:
        projects_by_id: Dict[str, Project] = {p.id: p for p in self.user_context.projects}
        employees_by_id: Dict[str, Employee] = {e.id: e for e in self.user_context.employees}

        for summary in self.user_context.time_summaries_by_project:
            project = projects_by_id.get(summary.project)
            if project is not None:
                project.time_summaries.append(summary)

        for summary in self.user_context.time_summaries_by_employee:
            employee = employees_by_id.get(summary.employee)
            if employee is not None:
                employee.time_summaries.append(summary)

    # Single-call convenience accessors
