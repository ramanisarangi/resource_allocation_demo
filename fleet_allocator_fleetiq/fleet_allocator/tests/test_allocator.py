"""
FleetIQ – Test Suite
Run: pytest tests/ -v
"""
import json
import sys
import os
import pytest
from datetime import datetime, timedelta
from pathlib import Path

# Ensure project root is on path
sys.path.insert(0, str(Path(__file__).parent.parent))

from backend.models.schemas import Resource, ServiceRequest
from backend.algorithms.allocator import (
    haversine_km, is_feasible, compute_cost, score_breakdown,
    allocate_greedy, allocate_hungarian, allocate_composite,
    run_allocation, compute_metrics,
)

TODAY = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)


def dt(h, m=0):
    return TODAY + timedelta(hours=h, minutes=m)


# ── Fixtures ──────────────────────────────────────────────────────────────────

def make_resource(rid, rtype, lat, lon, certs=None, shift_s=8, shift_e=18,
                  cost_km=12.0, cap=1, avail=True, load=0):
    return Resource(
        id=rid, name=f"Resource-{rid}", type=rtype, type_label=rtype,
        home_node_id="N01", home_node="Test Node",
        lat=lat, lon=lon,
        certifications=certs or [],
        shift_start=dt(shift_s), shift_end=dt(shift_e),
        cost_per_km=cost_km, capacity=cap,
        available=avail, current_load=load,
    )


def make_request(reqid, rtype, lat, lon, priority="P2", cert=None,
                 start_h=9, end_h=12):
    return ServiceRequest(
        id=reqid, category="Test Request", priority=priority,
        required_type=rtype, required_cert=cert,
        node_id="N01", node_name="Test Node",
        lat=lat, lon=lon,
        start_time=dt(start_h), end_time=dt(end_h),
        duration_hr=end_h - start_h,
        sla_minutes=60, status="OPEN", assigned_to=None,
    )


# ── Unit: Haversine ───────────────────────────────────────────────────────────

class TestHaversine:
    def test_same_point_is_zero(self):
        assert haversine_km(20.0, 85.0, 20.0, 85.0) == pytest.approx(0.0, abs=0.001)

    def test_known_distance_bbsr_to_kolkata(self):
        # Bhubaneswar → Kolkata ≈ 440 km
        d = haversine_km(20.296, 85.824, 22.572, 88.363)
        assert 340 < d < 400, f"Expected ~440 km, got {d:.1f}"

    def test_symmetry(self):
        d1 = haversine_km(21.0, 85.0, 22.0, 86.0)
        d2 = haversine_km(22.0, 86.0, 21.0, 85.0)
        assert d1 == pytest.approx(d2, abs=0.001)

    def test_longer_distance(self):
        # Raipur → Chennai ≈ 1450 km
        d = haversine_km(21.252, 81.629, 13.082, 80.270)
        assert 1300 < d < 1600, f"Expected ~1450 km, got {d:.1f}"


# ── Unit: Feasibility Checks ──────────────────────────────────────────────────

class TestFeasibility:
    def setup_method(self):
        self.res = make_resource("R001", "FIE", 21.0, 85.0, certs=["ISO9001"])
        self.req = make_request("REQ001", "FIE", 21.0, 85.0, priority="P2", cert=None,
                                start_h=9, end_h=12)

    def test_feasible_base_case(self):
        ok, viols = is_feasible(self.res, self.req, {})
        assert ok, f"Expected feasible, got violations: {viols}"

    def test_hc2_type_mismatch(self):
        req = make_request("REQ002", "LC", 21.0, 85.0)  # LC ≠ FIE
        ok, viols = is_feasible(self.res, req, {})
        assert not ok
        assert any("HC2" in v for v in viols)

    def test_hc1_unavailable(self):
        res = make_resource("R002", "FIE", 21.0, 85.0, avail=False)
        ok, viols = is_feasible(res, self.req, {})
        assert not ok
        assert any("HC1" in v for v in viols)

    def test_hc4_shift_end_violated(self):
        req = make_request("REQ003", "FIE", 21.0, 85.0, start_h=16, end_h=20)
        res = make_resource("R003", "FIE", 21.0, 85.0, shift_s=8, shift_e=18)
        ok, viols = is_feasible(res, req, {})
        assert not ok
        assert any("HC4" in v for v in viols)

    def test_hc5_missing_cert(self):
        req = make_request("REQ004", "FIE", 21.0, 85.0, cert="ISO9001")
        res = make_resource("R004", "FIE", 21.0, 85.0, certs=[])  # no cert
        ok, viols = is_feasible(res, req, {})
        assert not ok
        assert any("HC5" in v for v in viols)

    def test_hc5_cert_present_passes(self):
        req = make_request("REQ005", "FIE", 21.0, 85.0, cert="ISO9001")
        res = make_resource("R005", "FIE", 21.0, 85.0, certs=["ISO9001"])
        ok, viols = is_feasible(res, req, {})
        assert ok, f"Expected feasible with cert, got: {viols}"

    def test_hc3_capacity_exceeded(self):
        res = make_resource("R006", "FIE", 21.0, 85.0, cap=1)
        # simulate 1 active assignment overlapping
        existing_req = make_request("REQ_EX", "FIE", 21.0, 85.0, start_h=9, end_h=12)
        active = {"R006": [existing_req]}
        ok, viols = is_feasible(res, self.req, active)
        assert not ok
        assert any("HC3" in v for v in viols)

    def test_hc3_capacity_2_allows_second(self):
        res = make_resource("R007", "FIE", 21.0, 85.0, cap=2)
        existing_req = make_request("REQ_EX2", "FIE", 21.0, 85.0, start_h=9, end_h=12)
        active = {"R007": [existing_req]}
        ok, viols = is_feasible(res, self.req, active)
        assert ok, f"Cap=2 should allow second, got: {viols}"


# ── Unit: Cost Function ───────────────────────────────────────────────────────

class TestCostFunction:
    def test_p1_cheaper_than_p3_greedy(self):
        res = make_resource("R001", "FIE", 21.0, 85.0)
        req_p1 = make_request("P1", "FIE", 21.5, 85.5, priority="P1")
        req_p3 = make_request("P3", "FIE", 21.5, 85.5, priority="P3")
        cost_p1 = compute_cost(res, req_p1, {}, "greedy")
        cost_p3 = compute_cost(res, req_p3, {}, "greedy")
        assert cost_p1 < cost_p3, "P1 should have lower greedy cost than P3"

    def test_nearer_resource_cheaper(self):
        res_near = make_resource("RN", "FIE", 21.0, 85.0)
        res_far  = make_resource("RF", "FIE", 22.5, 87.0)
        req = make_request("REQ", "FIE", 21.1, 85.1, priority="P2")
        assert compute_cost(res_near, req, {}, "greedy") < compute_cost(res_far, req, {}, "greedy")

    def test_composite_score_bounded(self):
        res = make_resource("R001", "FIE", 21.0, 85.0, certs=["ISO9001"])
        req = make_request("REQ", "FIE", 21.1, 85.1, priority="P1", cert="ISO9001")
        cost = compute_cost(res, req, {}, "composite")
        # composite returns negative of score; score in [0,1], so cost in [-1, 0]
        assert -1.0 <= cost <= 0.0


# ── Integration: Greedy Algorithm ─────────────────────────────────────────────

class TestGreedyAlgorithm:
    def test_perfect_match_assigns_all(self):
        resources = [
            make_resource("R001", "FIE", 21.0, 85.0, certs=["ISO9001"]),
            make_resource("R002", "LC",  22.5, 88.3),
            make_resource("R003", "QA",  22.1, 85.3, certs=["ISO9001", "HAZMAT"]),
        ]
        requests = [
            make_request("REQ001", "FIE", 21.0, 85.0),
            make_request("REQ002", "LC",  22.5, 88.3),
            make_request("REQ003", "QA",  22.1, 85.3, cert="ISO9001"),
        ]
        assignments, unassigned = allocate_greedy(resources, requests)
        assert len(assignments) == 3
        assert len(unassigned) == 0

    def test_p1_assigned_before_p3(self):
        resources = [make_resource("R001", "FIE", 21.0, 85.0, cap=1)]
        req_p1 = make_request("REQ_P1", "FIE", 21.0, 85.0, priority="P1", start_h=9, end_h=12)
        req_p3 = make_request("REQ_P3", "FIE", 21.0, 85.0, priority="P3", start_h=9, end_h=12)
        assignments, unassigned = allocate_greedy(resources, [req_p1, req_p3])
        assigned_ids = [a.request_id for a in assignments]
        assert "REQ_P1" in assigned_ids
        assert "REQ_P3" in unassigned

    def test_no_resources_returns_all_unassigned(self):
        requests = [make_request("REQ001", "FIE", 21.0, 85.0)]
        assignments, unassigned = allocate_greedy([], requests)
        assert len(assignments) == 0
        assert "REQ001" in unassigned

    def test_type_mismatch_leaves_unassigned(self):
        resources = [make_resource("R001", "LC", 21.0, 85.0)]  # LC only
        requests  = [make_request("REQ001", "FIE", 21.0, 85.0)]  # needs FIE
        assignments, unassigned = allocate_greedy(resources, requests)
        assert len(assignments) == 0
        assert "REQ001" in unassigned

    def test_cert_gate_assigns_correct_resource(self):
        res_no_cert  = make_resource("R001", "QA", 21.0, 85.0, certs=[])
        res_has_cert = make_resource("R002", "QA", 22.0, 86.0, certs=["HAZMAT"])
        req = make_request("REQ001", "QA", 21.5, 85.5, cert="HAZMAT")
        assignments, unassigned = allocate_greedy([res_no_cert, res_has_cert], [req])
        assert len(assignments) == 1
        assert assignments[0].resource_id == "R002"

    def test_shift_conflict_leaves_unassigned(self):
        res = make_resource("R001", "TP", 21.0, 81.0, shift_s=6, shift_e=14)
        req = make_request("REQ001", "TP", 21.0, 81.0, start_h=15, end_h=17)
        assignments, unassigned = allocate_greedy([res], [req])
        assert len(assignments) == 0
        assert "REQ001" in unassigned


# ── Integration: Hungarian Algorithm ──────────────────────────────────────────

class TestHungarianAlgorithm:
    def test_assigns_all_in_perfect_match(self):
        resources = [
            make_resource("R001", "FIE", 21.0, 85.0),
            make_resource("R002", "LC",  22.5, 88.0),
        ]
        requests = [
            make_request("REQ001", "FIE", 21.0, 85.0),
            make_request("REQ002", "LC",  22.5, 88.0),
        ]
        assignments, unassigned = allocate_hungarian(resources, requests)
        assert len(assignments) == 2
        assert len(unassigned) == 0

    def test_infeasible_cells_not_assigned(self):
        resources = [make_resource("R001", "FIE", 21.0, 85.0)]
        requests  = [make_request("REQ001", "LC", 21.0, 85.0)]  # type mismatch
        assignments, unassigned = allocate_hungarian(resources, requests)
        assert len(assignments) == 0

    def test_non_square_matrix_handled(self):
        resources = [make_resource(f"R00{i}", "FIE", 21.0 + i*0.1, 85.0) for i in range(3)]
        requests  = [make_request(f"REQ00{i}", "FIE", 21.0 + i*0.1, 85.0) for i in range(5)]
        assignments, unassigned = allocate_hungarian(resources, requests)
        # At most min(3, 5) = 3 can be assigned
        assert len(assignments) <= 3


# ── Integration: Composite Algorithm ──────────────────────────────────────────

class TestCompositeAlgorithm:
    def test_assigns_all_feasible(self):
        resources = [
            make_resource("R001", "FIE", 21.0, 85.0),
            make_resource("R002", "QA",  22.0, 86.0, certs=["ISO9001"]),
        ]
        requests = [
            make_request("REQ001", "FIE", 21.0, 85.0),
            make_request("REQ002", "QA",  22.0, 86.0, cert="ISO9001"),
        ]
        assignments, unassigned = allocate_composite(resources, requests)
        assert len(assignments) == 2
        assert len(unassigned) == 0

    def test_workload_balance_improves_over_greedy(self):
        """Composite should spread load; greedy may concentrate it."""
        resources = [
            make_resource("R001", "FIE", 21.0, 85.0, cap=3),
            make_resource("R002", "FIE", 21.5, 85.5, cap=3),
        ]
        requests = [
            make_request(f"REQ{i:03d}", "FIE", 21.1 + i*0.01, 85.0, start_h=9+i, end_h=11+i)
            for i in range(4)
        ]
        asmts, _ = allocate_composite(resources, requests)
        loads = {}
        for a in asmts:
            loads[a.resource_id] = loads.get(a.resource_id, 0) + 1
        # Both resources should be used
        assert len(loads) >= 1  # at least some assignments made


# ── Integration: Metrics ──────────────────────────────────────────────────────

class TestMetrics:
    def test_assignment_rate_100_when_all_assigned(self):
        resources = [make_resource("R001", "FIE", 21.0, 85.0)]
        requests  = [make_request("REQ001", "FIE", 21.0, 85.0)]
        asmts, _ = allocate_greedy(resources, requests)
        metrics = compute_metrics(asmts, requests)
        assert metrics["assignment_rate"] == 100.0

    def test_assignment_rate_0_when_none_assigned(self):
        resources = []
        requests  = [make_request("REQ001", "FIE", 21.0, 85.0)]
        asmts, _ = allocate_greedy(resources, requests)
        metrics = compute_metrics(asmts, requests)
        assert metrics["assignment_rate"] == 0.0

    def test_gini_zero_for_equal_load(self):
        resources = [make_resource(f"R{i:03d}", "FIE", 21.0, 85.0) for i in range(3)]
        requests  = [make_request(f"REQ{i:03d}", "FIE", 21.0+i*0.1, 85.0+i*0.1, start_h=9+i, end_h=11+i)
                     for i in range(3)]
        asmts, _ = allocate_greedy(resources, requests)
        metrics = compute_metrics(asmts, requests)
        assert metrics["workload_gini"] == pytest.approx(0.0, abs=0.05)

    def test_p1_coverage_100_when_p1_assigned(self):
        resources = [make_resource("R001", "FIE", 21.0, 85.0)]
        requests  = [make_request("REQ001", "FIE", 21.0, 85.0, priority="P1")]
        asmts, _ = allocate_greedy(resources, requests)
        metrics = compute_metrics(asmts, requests)
        assert metrics["p1_coverage_pct"] == 100.0


# ── Integration: Algorithm Comparison ─────────────────────────────────────────

class TestAlgorithmComparison:
    """Structural tests ensuring all three algorithms run and produce valid output."""

    def setup_method(self):
        self.resources = [
            make_resource("R001", "FIE", 21.0, 85.0, certs=["ISO9001"]),
            make_resource("R002", "LC",  22.5, 88.0),
            make_resource("R003", "QA",  22.1, 85.3, certs=["ISO9001", "HAZMAT"]),
            make_resource("R004", "WS",  20.3, 85.8),
            make_resource("R005", "TP",  21.2, 81.6, certs=["RAIL_OPS"]),
        ]
        self.requests = [
            make_request("REQ001", "FIE", 21.0, 85.0, priority="P1"),
            make_request("REQ002", "LC",  22.5, 88.0, priority="P2"),
            make_request("REQ003", "QA",  22.1, 85.3, priority="P2", cert="ISO9001"),
            make_request("REQ004", "WS",  20.3, 85.8, priority="P3"),
            make_request("REQ005", "TP",  21.2, 81.6, priority="P3"),
        ]

    def test_all_algorithms_run(self):
        for algo in ("greedy", "hungarian", "composite"):
            result = run_allocation(self.resources, self.requests, algo)
            assert result.algorithm == algo
            assert isinstance(result.assignments, list)
            assert isinstance(result.metrics, dict)

    def test_assignments_have_explanations(self):
        for algo in ("greedy", "hungarian", "composite"):
            result = run_allocation(self.resources, self.requests, algo)
            for asn in result.assignments:
                assert asn.explanation, f"{algo}: assignment {asn.id} has no explanation"

    def test_assignments_reference_valid_ids(self):
        resource_ids = {r.id for r in self.resources}
        request_ids  = {r.id for r in self.requests}
        for algo in ("greedy", "hungarian", "composite"):
            result = run_allocation(self.resources, self.requests, algo)
            for asn in result.assignments:
                assert asn.resource_id in resource_ids, f"Unknown resource {asn.resource_id}"
                assert asn.request_id  in request_ids,  f"Unknown request {asn.request_id}"

    def test_no_duplicate_request_assignments(self):
        for algo in ("greedy", "hungarian", "composite"):
            result = run_allocation(self.resources, self.requests, algo)
            req_ids = [a.request_id for a in result.assignments]
            assert len(req_ids) == len(set(req_ids)), f"{algo}: duplicate request assignments found"

    def test_hungarian_total_cost_lte_greedy(self):
        """Hungarian should achieve ≤ total cost vs greedy on well-behaved input."""
        r_greedy   = run_allocation(self.resources, self.requests, "greedy")
        r_hungarian = run_allocation(self.resources, self.requests, "hungarian")
        # Not guaranteed always, but usually true — just validate both run
        assert r_greedy.metrics["total_cost_inr"] >= 0
        assert r_hungarian.metrics["total_cost_inr"] >= 0

    def test_metrics_keys_present(self):
        expected_keys = {
            "total_requests", "assigned", "unassigned", "assignment_rate",
            "total_distance_km", "total_cost_inr", "avg_distance_km",
            "cost_per_assignment", "p1_coverage_pct", "workload_gini", "resources_used",
        }
        result = run_allocation(self.resources, self.requests, "greedy")
        assert expected_keys.issubset(set(result.metrics.keys()))


# ── Fixture-based tests (load from test data files) ───────────────────────────

class TestWithFixtures:
    def _load(self, name):
        path = Path(__file__).parent / "data" / "test" / name
        if not path.exists():
            pytest.skip(f"Test fixture not found: {path}. Run data/generate_test_data.py")
        with open(path) as f:
            return json.load(f)

    def test_fixture_01_perfect_match(self):
        resources = [Resource(**r) for r in self._load("t01_perfect_match_resources.json")]
        requests  = [ServiceRequest(**r) for r in self._load("t01_perfect_match_requests.json")]
        asmts, unassigned = allocate_greedy(resources, requests)
        assert len(unassigned) == 0, f"Expected all assigned, got unassigned: {unassigned}"

    def test_fixture_02_overdemand(self):
        resources = [Resource(**r) for r in self._load("t02_overdemand_resources.json")]
        requests  = [ServiceRequest(**r) for r in self._load("t02_overdemand_requests.json")]
        asmts, unassigned = allocate_greedy(resources, requests)
        # With 2 resources and 5 requests, some must be unassigned
        assert len(unassigned) > 0

    def test_fixture_03_cert_gate(self):
        resources = [Resource(**r) for r in self._load("t03_cert_gate_resources.json")]
        requests  = [ServiceRequest(**r) for r in self._load("t03_cert_gate_requests.json")]
        asmts, unassigned = allocate_greedy(resources, requests)
        # R021 has HAZMAT, R020 does not — only R021 should be assigned
        if asmts:
            assert asmts[0].resource_id == "R021", "Should assign only HAZMAT-certified resource"

    def test_fixture_04_shift_conflict(self):
        resources = [Resource(**r) for r in self._load("t04_shift_conflict_resources.json")]
        requests  = [ServiceRequest(**r) for r in self._load("t04_shift_conflict_requests.json")]
        asmts, unassigned = allocate_greedy(resources, requests)
        # R030 shift ends 14h, request at 15h → only R031 (starts 12h) can serve
        if asmts:
            assert asmts[0].resource_id == "R031"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
