"""
FleetIQ – Test Data Generator
Generates deterministic, boundary-condition test fixtures.
Run: python generate_test_data.py
Output: data/test/*.json
"""

import json
from datetime import datetime, timedelta
from pathlib import Path

TODAY = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)


def iso(h, m=0):
    return (TODAY + timedelta(hours=h, minutes=m)).isoformat()


def save_json(obj, path):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as f:
        json.dump(obj, f, indent=2)
    print(f"  Saved → {path}")


# ── Fixture 1: Perfect 1-to-1 match (3 resources, 3 requests) ────────────────
PERFECT_MATCH_RESOURCES = [
    {"id": "R001", "name": "FIE-Alpha",  "type": "FIE", "type_label": "Field Inspection Engineer",
     "lat": 21.018, "lon": 85.855, "certifications": ["ISO9001"],
     "shift_start": iso(8), "shift_end": iso(18), "cost_per_km": 12.0,
     "capacity": 1, "available": True, "current_load": 0, "home_node_id": "N03", "home_node": "Kalinganagar Plant"},
    {"id": "R002", "name": "LC-Bravo",   "type": "LC",  "type_label": "Logistics Coordinator",
     "lat": 22.572, "lon": 88.363, "certifications": ["CUSTOMS"],
     "shift_start": iso(7), "shift_end": iso(19), "cost_per_km": 10.0,
     "capacity": 1, "available": True, "current_load": 0, "home_node_id": "N07", "home_node": "Kolkata DC"},
    {"id": "R003", "name": "QA-Charlie", "type": "QA",  "type_label": "Quality Auditor",
     "lat": 22.104, "lon": 85.362, "certifications": ["ISO9001", "HAZMAT"],
     "shift_start": iso(6), "shift_end": iso(18), "cost_per_km": 15.0,
     "capacity": 1, "available": True, "current_load": 0, "home_node_id": "N01", "home_node": "Barbil Mine"},
]

PERFECT_MATCH_REQUESTS = [
    {"id": "REQ0001", "category": "Inbound Material Inspection", "priority": "P2",
     "required_type": "FIE", "required_cert": None,
     "lat": 21.018, "lon": 85.855, "node_id": "N03", "node_name": "Kalinganagar Plant",
     "start_time": iso(9), "end_time": iso(12), "duration_hr": 3,
     "sla_minutes": 60, "status": "OPEN", "assigned_to": None},
    {"id": "REQ0002", "category": "Routine Logistics Support", "priority": "P3",
     "required_type": "LC", "required_cert": None,
     "lat": 22.572, "lon": 88.363, "node_id": "N07", "node_name": "Kolkata DC",
     "start_time": iso(10), "end_time": iso(12), "duration_hr": 2,
     "sla_minutes": 120, "status": "OPEN", "assigned_to": None},
    {"id": "REQ0003", "category": "Vendor Quality Audit", "priority": "P2",
     "required_type": "QA", "required_cert": "ISO9001",
     "lat": 22.104, "lon": 85.362, "node_id": "N01", "node_name": "Barbil Mine",
     "start_time": iso(8), "end_time": iso(14), "duration_hr": 6,
     "sla_minutes": 60, "status": "OPEN", "assigned_to": None},
]

# ── Fixture 2: Over-demand (2 resources, 5 requests) ─────────────────────────
OVERDEMAND_RESOURCES = [
    {"id": "R010", "name": "FIE-Delta", "type": "FIE", "type_label": "Field Inspection Engineer",
     "lat": 20.296, "lon": 85.824, "certifications": ["ISO9001"],
     "shift_start": iso(8), "shift_end": iso(18), "cost_per_km": 12.0,
     "capacity": 2, "available": True, "current_load": 0, "home_node_id": "N05", "home_node": "Bhubaneswar Hub"},
    {"id": "R011", "name": "WS-Echo",  "type": "WS",  "type_label": "Warehouse Supervisor",
     "lat": 20.316, "lon": 86.609, "certifications": [],
     "shift_start": iso(9), "shift_end": iso(17), "cost_per_km": 9.0,
     "capacity": 1, "available": True, "current_load": 0, "home_node_id": "N08", "home_node": "Paradip Port"},
]

OVERDEMAND_REQUESTS = [
    {"id": "REQ0010", "category": "Critical Shipment Hold", "priority": "P1",
     "required_type": "FIE", "required_cert": None,
     "lat": 20.316, "lon": 86.609, "node_id": "N08", "node_name": "Paradip Port",
     "start_time": iso(9), "end_time": iso(13), "duration_hr": 4, "sla_minutes": 30, "status": "OPEN", "assigned_to": None},
    {"id": "REQ0011", "category": "Inbound Material Inspection", "priority": "P2",
     "required_type": "FIE", "required_cert": None,
     "lat": 20.296, "lon": 85.824, "node_id": "N05", "node_name": "Bhubaneswar Hub",
     "start_time": iso(10), "end_time": iso(13), "duration_hr": 3, "sla_minutes": 60, "status": "OPEN", "assigned_to": None},
    {"id": "REQ0012", "category": "Warehouse Exception", "priority": "P3",
     "required_type": "WS", "required_cert": None,
     "lat": 20.296, "lon": 85.824, "node_id": "N05", "node_name": "Bhubaneswar Hub",
     "start_time": iso(10), "end_time": iso(12), "duration_hr": 2, "sla_minutes": 120, "status": "OPEN", "assigned_to": None},
    {"id": "REQ0013", "category": "Warehouse Exception", "priority": "P3",
     "required_type": "WS", "required_cert": None,
     "lat": 20.316, "lon": 86.609, "node_id": "N08", "node_name": "Paradip Port",
     "start_time": iso(11), "end_time": iso(13), "duration_hr": 2, "sla_minutes": 120, "status": "OPEN", "assigned_to": None},
    {"id": "REQ0014", "category": "Vendor Quality Audit", "priority": "P2",
     "required_type": "FIE", "required_cert": "ISO9001",
     "lat": 21.018, "lon": 85.855, "node_id": "N03", "node_name": "Kalinganagar Plant",
     "start_time": iso(14), "end_time": iso(20), "duration_hr": 6, "sla_minutes": 60, "status": "OPEN", "assigned_to": None},
]

# ── Fixture 3: Certification gate (resource lacks cert) ──────────────────────
CERT_GATE_RESOURCES = [
    {"id": "R020", "name": "QA-Foxtrot", "type": "QA", "type_label": "Quality Auditor",
     "lat": 22.800, "lon": 86.185, "certifications": ["ISO9001"],   # NO HAZMAT
     "shift_start": iso(8), "shift_end": iso(18), "cost_per_km": 14.0,
     "capacity": 1, "available": True, "current_load": 0, "home_node_id": "N04", "home_node": "Jamshedpur Plant"},
    {"id": "R021", "name": "QA-Golf",    "type": "QA", "type_label": "Quality Auditor",
     "lat": 23.344, "lon": 85.310, "certifications": ["ISO9001", "HAZMAT"],  # HAS HAZMAT
     "shift_start": iso(7), "shift_end": iso(19), "cost_per_km": 18.0,
     "capacity": 1, "available": True, "current_load": 0, "home_node_id": "N06", "home_node": "Ranchi Hub"},
]

CERT_GATE_REQUESTS = [
    {"id": "REQ0020", "category": "Regulatory Compliance Check", "priority": "P2",
     "required_type": "QA", "required_cert": "HAZMAT",
     "lat": 22.800, "lon": 86.185, "node_id": "N04", "node_name": "Jamshedpur Plant",
     "start_time": iso(9), "end_time": iso(14), "duration_hr": 5, "sla_minutes": 60, "status": "OPEN", "assigned_to": None},
]

# ── Fixture 4: Shift conflict (resource shift ends before request) ────────────
SHIFT_CONFLICT_RESOURCES = [
    {"id": "R030", "name": "TP-Hotel", "type": "TP", "type_label": "Transport Planner",
     "lat": 21.252, "lon": 81.629, "certifications": ["RAIL_OPS"],
     "shift_start": iso(6), "shift_end": iso(14),   # ends at 14:00
     "cost_per_km": 11.0, "capacity": 1, "available": True, "current_load": 0,
     "home_node_id": "N10", "home_node": "Raipur Rail Yard"},
    {"id": "R031", "name": "TP-India", "type": "TP", "type_label": "Transport Planner",
     "lat": 21.252, "lon": 81.629, "certifications": ["RAIL_OPS", "CUSTOMS"],
     "shift_start": iso(12), "shift_end": iso(22),  # starts at 12:00
     "cost_per_km": 13.0, "capacity": 1, "available": True, "current_load": 0,
     "home_node_id": "N10", "home_node": "Raipur Rail Yard"},
]

SHIFT_CONFLICT_REQUESTS = [
    {"id": "REQ0030", "category": "Routine Logistics Support", "priority": "P3",
     "required_type": "TP", "required_cert": None,
     "lat": 21.252, "lon": 81.629, "node_id": "N10", "node_name": "Raipur Rail Yard",
     "start_time": iso(15), "end_time": iso(17), "duration_hr": 2,  # 15–17h (R030 shift ended)
     "sla_minutes": 120, "status": "OPEN", "assigned_to": None},
]


if __name__ == "__main__":
    print("Generating FleetIQ test fixtures …")
    save_json(PERFECT_MATCH_RESOURCES,  "data/test/t01_perfect_match_resources.json")
    save_json(PERFECT_MATCH_REQUESTS,   "data/test/t01_perfect_match_requests.json")
    save_json(OVERDEMAND_RESOURCES,     "data/test/t02_overdemand_resources.json")
    save_json(OVERDEMAND_REQUESTS,      "data/test/t02_overdemand_requests.json")
    save_json(CERT_GATE_RESOURCES,      "data/test/t03_cert_gate_resources.json")
    save_json(CERT_GATE_REQUESTS,       "data/test/t03_cert_gate_requests.json")
    save_json(SHIFT_CONFLICT_RESOURCES, "data/test/t04_shift_conflict_resources.json")
    save_json(SHIFT_CONFLICT_REQUESTS,  "data/test/t04_shift_conflict_requests.json")
    print("Done.")
