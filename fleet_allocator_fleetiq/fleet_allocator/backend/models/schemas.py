"""
FleetIQ – Data Models
Uses Pydantic v2 when available, falls back to dataclasses for local testing.
FastAPI requires Pydantic; install requirements.txt before running the server.
"""
from __future__ import annotations

try:
    from pydantic import BaseModel, Field
    _PYDANTIC = True
except ImportError:
    _PYDANTIC = False

from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional


if _PYDANTIC:
    class Node(BaseModel):
        id: str; name: str; lat: float; lon: float; type: str

    class Resource(BaseModel):
        id: str; name: str; type: str; type_label: str
        home_node_id: str; home_node: str; lat: float; lon: float
        certifications: List[str] = Field(default_factory=list)
        shift_start: datetime; shift_end: datetime
        cost_per_km: float; capacity: int = 1
        available: bool = True; current_load: int = 0

    class ServiceRequest(BaseModel):
        id: str; category: str; priority: str; required_type: str
        node_id: str; node_name: str; lat: float; lon: float
        start_time: datetime; end_time: datetime; duration_hr: int
        required_cert: Optional[str] = None; description: Optional[str] = None
        sla_minutes: int = 60; status: str = "OPEN"; assigned_to: Optional[str] = None

    class ScoreBreakdown(BaseModel):
        travel_score: float; priority_score: float
        balance_score: float; cert_bonus: float; total_score: float

    class AlternativeCandidate(BaseModel):
        resource_id: str; resource_name: str; score: float
        rejection_reason: Optional[str] = None

    class Assignment(BaseModel):
        id: str; request_id: str; resource_id: str; resource_name: str
        resource_type: str; request_category: str; request_priority: str
        node_name: str; travel_distance_km: float; travel_cost_inr: float
        algorithm: str; explanation: str
        timestamp: datetime = Field(default_factory=datetime.utcnow)
        score_breakdown: Optional[ScoreBreakdown] = None
        alternatives_considered: List[AlternativeCandidate] = Field(default_factory=list)
        constraints_applied: List[str] = Field(default_factory=list)

    class AllocationRequest(BaseModel):
        resources: List[Resource]; requests: List[ServiceRequest]
        algorithm: str = "greedy"

    class AllocationResult(BaseModel):
        algorithm: str; assignments: List[Assignment]
        metrics: dict; unassigned_requests: List[str]; run_time_ms: float

else:
    def _parse_dt(v):
        if isinstance(v, datetime): return v
        return datetime.fromisoformat(str(v))

    @dataclass
    class Node:
        id: str; name: str; lat: float; lon: float; type: str

    @dataclass
    class Resource:
        id: str; name: str; type: str; type_label: str
        home_node_id: str; home_node: str; lat: float; lon: float
        certifications: List[str] = field(default_factory=list)
        shift_start: datetime = None; shift_end: datetime = None
        cost_per_km: float = 12.0; capacity: int = 1
        available: bool = True; current_load: int = 0
        def __post_init__(self):
            self.shift_start = _parse_dt(self.shift_start)
            self.shift_end   = _parse_dt(self.shift_end)

    @dataclass
    class ServiceRequest:
        id: str; category: str; priority: str; required_type: str
        node_id: str; node_name: str; lat: float; lon: float
        start_time: datetime = None; end_time: datetime = None
        duration_hr: int = 2; required_cert: Optional[str] = None
        description: Optional[str] = None; sla_minutes: int = 60
        status: str = "OPEN"; assigned_to: Optional[str] = None
        def __post_init__(self):
            self.start_time = _parse_dt(self.start_time)
            self.end_time   = _parse_dt(self.end_time)

    @dataclass
    class ScoreBreakdown:
        travel_score: float; priority_score: float
        balance_score: float; cert_bonus: float; total_score: float

    @dataclass
    class AlternativeCandidate:
        resource_id: str; resource_name: str; score: float
        rejection_reason: Optional[str] = None

    @dataclass
    class Assignment:
        id: str; request_id: str; resource_id: str; resource_name: str
        resource_type: str; request_category: str; request_priority: str
        node_name: str; travel_distance_km: float; travel_cost_inr: float
        algorithm: str; explanation: str
        timestamp: datetime = field(default_factory=datetime.utcnow)
        score_breakdown: Optional[ScoreBreakdown] = None
        alternatives_considered: List[AlternativeCandidate] = field(default_factory=list)
        constraints_applied: List[str] = field(default_factory=list)

    @dataclass
    class AllocationRequest:
        resources: List[Resource]; requests: List[ServiceRequest]
        algorithm: str = "greedy"

    @dataclass
    class AllocationResult:
        algorithm: str; assignments: List[Assignment]
        metrics: dict; unassigned_requests: List[str]; run_time_ms: float
