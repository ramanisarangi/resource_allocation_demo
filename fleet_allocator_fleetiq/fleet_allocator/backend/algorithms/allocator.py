"""
FleetIQ – Allocation Algorithms
Three strategies:
  1. greedy    – priority-ordered sequential assignment (O(n·m))
  2. hungarian – batch optimal via scipy linear_sum_assignment (O(n³))
  3. composite – domain-heuristic with workload balance + 2-opt improvement
"""
from __future__ import annotations

import uuid
import math
from copy import deepcopy
from datetime import datetime
from typing import List, Dict, Optional, Tuple

import numpy as np
from scipy.optimize import linear_sum_assignment

from backend.models.schemas import (
    Resource, ServiceRequest, Assignment,
    ScoreBreakdown, AlternativeCandidate, AllocationResult,
)

# ── Priority weights ──────────────────────────────────────────────────────────
PRIORITY_WEIGHT = {"P1": 3.0, "P2": 2.0, "P3": 1.0}
INF_COST = 1e9   # sentinel for infeasible cells

# ── Haversine ─────────────────────────────────────────────────────────────────

def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    R = 6371.0
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi  = math.radians(lat2 - lat1)
    dlam  = math.radians(lon2 - lon1)
    a = math.sin(dphi/2)**2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlam/2)**2
    return 2 * R * math.asin(math.sqrt(a))


# ── Constraint checks ─────────────────────────────────────────────────────────

def is_feasible(resource: Resource, request: ServiceRequest,
                active_assignments: Dict[str, List[ServiceRequest]]) -> Tuple[bool, List[str]]:
    """Return (feasible, [constraint violations])."""
    violations = []

    # HC1 – Availability
    if not resource.available:
        violations.append("HC1: resource not available")

    # HC2 – Type match
    if resource.type != request.required_type:
        violations.append(f"HC2: type mismatch ({resource.type} ≠ {request.required_type})")

    # HC4 – Shift boundary
    if request.end_time > resource.shift_end:
        violations.append("HC4: request ends after shift ends")
    if request.start_time < resource.shift_start:
        violations.append("HC4: request starts before shift starts")

    # HC5 – Certification
    if request.required_cert and request.required_cert not in resource.certifications:
        violations.append(f"HC5: missing cert {request.required_cert}")

    # HC3 – Capacity (no overlapping active assignments exceeding capacity)
    if resource.id in active_assignments:
        overlaps = sum(
            1 for r in active_assignments[resource.id]
            if r.start_time < request.end_time and r.end_time > request.start_time
        )
        if overlaps >= resource.capacity:
            violations.append(f"HC3: capacity exceeded ({overlaps}/{resource.capacity})")

    return len(violations) == 0, violations


# ── Cost function ─────────────────────────────────────────────────────────────

def compute_cost(resource: Resource, request: ServiceRequest,
                 active_assignments: Dict[str, List[ServiceRequest]],
                 algo: str = "greedy") -> float:
    """
    Lower is better.
    greedy/hungarian: weighted travel cost normalised by priority.
    composite: multi-factor score (returned inverted so lower = better).
    """
    dist_km = haversine_km(resource.lat, resource.lon, request.lat, request.lon)
    travel_cost = dist_km * resource.cost_per_km

    if algo in ("greedy", "hungarian"):
        priority_divisor = PRIORITY_WEIGHT[request.priority]
        return travel_cost / priority_divisor

    # composite – build score (higher raw = better), then return negative
    max_dist = 2000.0  # rough max across the network
    travel_score    = max(0.0, 1 - dist_km / max_dist)
    priority_score  = PRIORITY_WEIGHT[request.priority] / 3.0
    load            = active_assignments.get(resource.id, [])
    balance_score   = max(0.0, 1 - len(load) / resource.capacity)
    cert_bonus      = 0.1 if request.required_cert and request.required_cert in resource.certifications else 0.0

    raw = 0.30 * travel_score + 0.40 * priority_score + 0.20 * balance_score + 0.10 * cert_bonus
    return -raw   # negate so min = best


def score_breakdown(resource: Resource, request: ServiceRequest,
                    active_assignments: Dict[str, List[ServiceRequest]]) -> ScoreBreakdown:
    dist_km = haversine_km(resource.lat, resource.lon, request.lat, request.lon)
    max_dist = 2000.0
    travel_score   = round(max(0.0, 1 - dist_km / max_dist), 3)
    priority_score = round(PRIORITY_WEIGHT[request.priority] / 3.0, 3)
    load           = active_assignments.get(resource.id, [])
    balance_score  = round(max(0.0, 1 - len(load) / resource.capacity), 3)
    cert_bonus     = round(0.1 if request.required_cert and request.required_cert in resource.certifications else 0.0, 3)
    total          = round(0.30 * travel_score + 0.40 * priority_score + 0.20 * balance_score + 0.10 * cert_bonus, 3)
    return ScoreBreakdown(
        travel_score=travel_score,
        priority_score=priority_score,
        balance_score=balance_score,
        cert_bonus=cert_bonus,
        total_score=total,
    )


def make_assignment(resource: Resource, request: ServiceRequest,
                    algorithm: str,
                    active_assignments: Dict[str, List[ServiceRequest]],
                    all_resources: List[Resource],
                    constraints_applied: List[str]) -> Assignment:
    dist_km = haversine_km(resource.lat, resource.lon, request.lat, request.lon)
    breakdown = score_breakdown(resource, request, active_assignments)

    # Top-3 alternatives
    alternatives = []
    for r in all_resources:
        if r.id == resource.id:
            continue
        ok, viols = is_feasible(r, request, active_assignments)
        alt_dist = haversine_km(r.lat, r.lon, request.lat, request.lon)
        if ok:
            alternatives.append(AlternativeCandidate(
                resource_id=r.id,
                resource_name=r.name,
                score=round(score_breakdown(r, request, active_assignments).total_score, 3),
            ))
        elif len(alternatives) < 2:
            alternatives.append(AlternativeCandidate(
                resource_id=r.id,
                resource_name=r.name,
                score=0.0,
                rejection_reason="; ".join(viols[:1]),
            ))
    alternatives.sort(key=lambda a: -a.score)
    alternatives = alternatives[:3]

    explanation = (
        f"Assigned {resource.name} ({resource.type}) to {request.category} at {request.node_name}. "
        f"Distance: {dist_km:.1f} km | Priority: {request.priority} | "
        f"Score: Travel={breakdown.travel_score}, Priority={breakdown.priority_score}, "
        f"Balance={breakdown.balance_score}, Cert={breakdown.cert_bonus}. "
        f"Algorithm: {algorithm.upper()}."
    )

    return Assignment(
        id=str(uuid.uuid4()),
        request_id=request.id,
        resource_id=resource.id,
        resource_name=resource.name,
        resource_type=resource.type,
        request_category=request.category,
        request_priority=request.priority,
        node_name=request.node_name,
        travel_distance_km=round(dist_km, 2),
        travel_cost_inr=round(dist_km * resource.cost_per_km, 2),
        algorithm=algorithm,
        explanation=explanation,
        score_breakdown=breakdown,
        alternatives_considered=alternatives,
        constraints_applied=constraints_applied,
    )


# ── Metrics ───────────────────────────────────────────────────────────────────

def compute_metrics(assignments: List[Assignment],
                    all_requests: List[ServiceRequest]) -> dict:
    n_total = len(all_requests)
    n_assigned = len(assignments)
    n_unassigned = n_total - n_assigned

    total_dist = sum(a.travel_distance_km for a in assignments)
    total_cost = sum(a.travel_cost_inr for a in assignments)
    p1_reqs    = [r for r in all_requests if r.priority == "P1"]
    p1_assigned = sum(1 for a in assignments if a.request_priority == "P1")

    # Workload Gini
    resource_loads: Dict[str, int] = {}
    for a in assignments:
        resource_loads[a.resource_id] = resource_loads.get(a.resource_id, 0) + 1
    loads = sorted(resource_loads.values()) if resource_loads else [0]
    n = len(loads)
    gini = sum(abs(loads[i] - loads[j]) for i in range(n) for j in range(n)) / (2 * n * sum(loads)) if sum(loads) > 0 else 0.0

    return {
        "total_requests":    n_total,
        "assigned":          n_assigned,
        "unassigned":        n_unassigned,
        "assignment_rate":   round(n_assigned / n_total * 100, 1) if n_total > 0 else 0,
        "total_distance_km": round(total_dist, 1),
        "total_cost_inr":    round(total_cost, 1),
        "avg_distance_km":   round(total_dist / n_assigned, 1) if n_assigned > 0 else 0,
        "cost_per_assignment": round(total_cost / n_assigned, 1) if n_assigned > 0 else 0,
        "p1_coverage_pct":   round(p1_assigned / len(p1_reqs) * 100, 1) if p1_reqs else 100.0,
        "workload_gini":     round(gini, 3),
        "resources_used":    len(resource_loads),
    }


# ── Algorithm 1: Greedy ───────────────────────────────────────────────────────

def allocate_greedy(resources: List[Resource],
                    requests: List[ServiceRequest]) -> Tuple[List[Assignment], List[str]]:
    resources = deepcopy(resources)
    requests  = sorted(deepcopy(requests), key=lambda r: -PRIORITY_WEIGHT[r.priority])

    active: Dict[str, List[ServiceRequest]] = {}
    assignments: List[Assignment] = []
    unassigned: List[str] = []

    for req in requests:
        best_cost = INF_COST
        best_res  = None
        best_constraints: List[str] = []

        for res in resources:
            ok, viols = is_feasible(res, req, active)
            if not ok:
                continue
            cost = compute_cost(res, req, active, algo="greedy")
            if cost < best_cost:
                best_cost = cost
                best_res  = res
                best_constraints = ["HC1", "HC2", "HC3", "HC4"] + (["HC5"] if req.required_cert else [])

        if best_res is None:
            unassigned.append(req.id)
        else:
            asn = make_assignment(best_res, req, "greedy", active, resources, best_constraints)
            assignments.append(asn)
            active.setdefault(best_res.id, []).append(req)

    return assignments, unassigned


# ── Algorithm 2: Hungarian ────────────────────────────────────────────────────

def allocate_hungarian(resources: List[Resource],
                       requests: List[ServiceRequest]) -> Tuple[List[Assignment], List[str]]:
    resources = deepcopy(resources)
    requests  = deepcopy(requests)

    n_req = len(requests)
    n_res = len(resources)

    # Build cost matrix (n_req × n_res)
    active: Dict[str, List[ServiceRequest]] = {}
    cost_matrix = np.full((n_req, n_res), INF_COST, dtype=float)

    for i, req in enumerate(requests):
        for j, res in enumerate(resources):
            ok, _ = is_feasible(res, req, active)
            if ok:
                cost_matrix[i, j] = compute_cost(res, req, active, algo="hungarian")

    # Pad to square if needed
    size = max(n_req, n_res)
    padded = np.full((size, size), INF_COST * 10, dtype=float)
    padded[:n_req, :n_res] = cost_matrix

    row_ind, col_ind = linear_sum_assignment(padded)

    assignments: List[Assignment] = []
    assigned_req_ids = set()

    for r, c in zip(row_ind, col_ind):
        if r >= n_req or c >= n_res:
            continue
        if cost_matrix[r, c] >= INF_COST:
            continue
        req = requests[r]
        res = resources[c]
        constraints = ["HC1", "HC2", "HC3", "HC4"] + (["HC5"] if req.required_cert else [])
        asn = make_assignment(res, req, "hungarian", active, resources, constraints)
        assignments.append(asn)
        active.setdefault(res.id, []).append(req)
        assigned_req_ids.add(req.id)

    unassigned = [r.id for r in requests if r.id not in assigned_req_ids]
    return assignments, unassigned


# ── Algorithm 3: Composite Heuristic ─────────────────────────────────────────

def allocate_composite(resources: List[Resource],
                       requests: List[ServiceRequest]) -> Tuple[List[Assignment], List[str]]:
    """
    Greedy seed with multi-factor score, then 2-opt improvement pass.
    """
    resources = deepcopy(resources)
    requests  = sorted(deepcopy(requests), key=lambda r: -PRIORITY_WEIGHT[r.priority])

    active: Dict[str, List[ServiceRequest]] = {}
    assignments: List[Assignment] = []
    assignment_map: Dict[str, Tuple[Resource, ServiceRequest]] = {}
    unassigned: List[str] = []

    # Initial greedy pass with composite cost
    for req in requests:
        best_cost = INF_COST
        best_res  = None

        for res in resources:
            ok, _ = is_feasible(res, req, active)
            if not ok:
                continue
            cost = compute_cost(res, req, active, algo="composite")
            if cost < best_cost:
                best_cost = cost
                best_res  = res

        if best_res is None:
            unassigned.append(req.id)
        else:
            constraints = ["HC1", "HC2", "HC3", "HC4", "SC1", "SC2", "SC3"] + (["HC5"] if req.required_cert else [])
            asn = make_assignment(best_res, req, "composite", active, resources, constraints)
            assignments.append(asn)
            active.setdefault(best_res.id, []).append(req)
            assignment_map[req.id] = (best_res, req)

    # 2-opt improvement: try swapping resource assignments between request pairs
    improved = True
    iterations = 0
    while improved and iterations < 20:
        improved = False
        iterations += 1
        for i in range(len(assignments)):
            for j in range(i + 1, len(assignments)):
                ai, aj = assignments[i], assignments[j]
                # res_i/req_i = resource & request for assignment i
                res_i, req_i = assignment_map.get(ai.request_id, (None, None))
                res_j, req_j = assignment_map.get(aj.request_id, (None, None))
                if res_i is None or res_j is None:
                    continue
                # Try swap: can res_i serve req_j and res_j serve req_i?
                ok_ij, _ = is_feasible(res_i, req_j, {k: v for k, v in active.items() if k != res_i.id})
                ok_ji, _ = is_feasible(res_j, req_i, {k: v for k, v in active.items() if k != res_j.id})
                if not (ok_ij and ok_ji):
                    continue
                old_cost = (compute_cost(res_i, req_i, active, "composite") +
                            compute_cost(res_j, req_j, active, "composite"))
                new_cost = (compute_cost(res_i, req_j, active, "composite") +
                            compute_cost(res_j, req_i, active, "composite"))
                if new_cost < old_cost - 1e-6:
                    constraints_i = assignments[i].constraints_applied
                    constraints_j = assignments[j].constraints_applied
                    new_ai = make_assignment(res_i, req_j, "composite", active, resources, constraints_i)
                    new_aj = make_assignment(res_j, req_i, "composite", active, resources, constraints_j)
                    assignments[i] = new_ai
                    assignments[j] = new_aj
                    assignment_map[req_j.id] = (res_i, req_j)
                    assignment_map[req_i.id] = (res_j, req_i)
                    improved = True

    return assignments, unassigned


# ── Public dispatcher ─────────────────────────────────────────────────────────

def run_allocation(resources: List[Resource],
                   requests: List[ServiceRequest],
                   algorithm: str,
                   run_time_ms: float = 0.0) -> AllocationResult:
    fn = {
        "greedy":    allocate_greedy,
        "hungarian": allocate_hungarian,
        "composite": allocate_composite,
    }.get(algorithm)
    if fn is None:
        raise ValueError(f"Unknown algorithm: {algorithm}")

    assignments, unassigned = fn(resources, requests)
    metrics = compute_metrics(assignments, requests)
    return AllocationResult(
        algorithm=algorithm,
        assignments=assignments,
        metrics=metrics,
        unassigned_requests=unassigned,
        run_time_ms=run_time_ms,
    )
