from typing import Dict, List, Literal, Optional, Any

from pydantic import BaseModel, Field


# ============================================================
# Core Structures
# ============================================================

class InputTask(BaseModel):
    """
    A solving task. Orchestrator passes it to solve() and validate().
    """
    text: str


class OutputResponse(BaseModel):
    """
    The answer to be submitted. Response = g(InputTask, DerivedFacts, DataContext)

    Lifecycle:
      - Produced by solve() (LLM + wrappers).
      - Validated deterministically by inverse_solve().
    """
    message: str


class DataContext(BaseModel):
    """
    Operational database is consist of tables as collection of pydantic object instances.
    It can be treated as Working memory where every object should be observable by LLM in their table.

    Lifecycle:
      - Built by deterministic wrapper code (optionally with paging aggregation).
      - Object storage mechanism is not specified but should be considered as actual snapshot of every deterministic wrapper call.
      - LLM cannot change working memory in solving process.
    """
    tables: Dict[str, Dict[id, BaseModel]] = Field(...,
                                                   description="Working memory is dict of pydantic objects list (entity_name -> list of objects)")


class APIRequest(BaseModel):
    """
    Minimal request representation for auditability.
    """
    method: Literal["GET", "POST", "PUT", "PATCH", "DELETE"]
    path: str
    body: Optional[Dict[str, Any]] = None


class APICall(BaseModel):
    """
    A single API call record.

    Lifecycle:
      - Recorded by deterministic wrapper.
      - Validator verifies response hash if response is present.
    """
    id: str
    req: APIRequest
    response: Optional[Dict[str, Any]] = None
    timestamp_ms: Optional[int] = None


class ExecutionTrace(BaseModel):
    """
    Deterministic trace of what solve() actually did via API wrappers.

    Lifecycle:
      - Depends on Task and the API responses.
      - The validator does NOT call API again for core checks (optional spot checks are outside kernel).
      - Recorded by wrappers.
      - Verified deterministically.
    """
    calls: List[APICall] = Field(..., description="List of API calls")
    artifacts: Dict[id, BaseModel] = Field(..., description="List of artifacts as entities")
