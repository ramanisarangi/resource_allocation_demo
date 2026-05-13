"""
FleetIQ – Sample Data Generator
Generates realistic supply chain resource allocation data for IndoSteel scenario.
Run: python generate_sample_data.py
Output: data/sample/*.json
"""

import json
import random
import uuid
from datetime import datetime, timedelta
from pathlib import Path

random.seed(42)

# ── Supply chain node locations ──────────────────────────────────────────────
NODES = [
    {"id": "N01", "name": "Barbil Mine Depot",        "lat": 22.104, "lon": 85.362, "type": "mine"},
    {"id": "N02", "name": "Noamundi Mine Depot",       "lat": 22.158, "lon": 85.503, "type": "mine"},
    {"id": "N03", "name": "Kalinganagar Plant",        "lat": 21.018, "lon": 85.855, "type": "plant"},
    {"id": "N04", "name": "Jamshedpur Plant",          "lat": 22.800, "lon": 86.185, "type": "plant"},
    {"id": "N05", "name": "Bhubaneswar Hub",           "lat": 20.296, "lon": 85.824, "type": "warehouse"},
    {"id": "N06", "name": "Ranchi Hub",                "lat": 23.344, "lon": 85.310, "type": "warehouse"},
    {"id": "N07", "name": "Kolkata Distribution DC",  "lat": 22.572, "lon": 88.363, "type": "warehouse"},
    {"id": "N08", "name": "Paradip Port Yard",         "lat": 20.316, "lon": 86.609, "type": "port"},
    {"id": "N09", "name": "Haldia Port Yard",          "lat": 22.025, "lon": 88.069, "type": "port"},
    {"id": "N10", "name": "Raipur Rail Yard",          "lat": 21.252, "lon": 81.629, "type": "railyard"},
    {"id": "N11", "name": "Pune OEM Zone",             "lat": 18.520, "lon": 73.856, "type": "customer"},
    {"id": "N12", "name": "Chennai OEM Zone",          "lat": 13.082, "lon": 80.270, "type": "customer"},
]

RESOURCE_TYPES = ["FIE", "LC", "WS", "QA", "TP"]
CERTIFICATIONS = ["ISO9001", "OHSAS18001", "HAZMAT", "CUSTOMS", "FMCG_AUDIT", "RAIL_OPS"]

RESOURCE_TYPE_CERTS = {
    "FIE": ["ISO9001", "OHSAS18001"],
    "LC":  ["CUSTOMS", "HAZMAT"],
    "WS":  ["ISO9001", "OHSAS18001"],
    "QA":  ["ISO9001", "FMCG_AUDIT", "HAZMAT"],
    "TP":  ["RAIL_OPS", "CUSTOMS"],
}

RESOURCE_TYPE_LABELS = {
    "FIE": "Field Inspection Engineer",
    "LC":  "Logistics Coordinator",
    "WS":  "Warehouse Supervisor",
    "QA":  "Quality Auditor",
    "TP":  "Transport Planner",
}

REQUEST_CATEGORIES = [
    {"cat": "Critical Shipment Hold",      "priority": "P1", "required_types": ["FIE", "LC"], "required_cert": None,        "duration_hr": 4},
    {"cat": "Customer Escalation",         "priority": "P1", "required_types": ["LC", "TP"],  "required_cert": None,        "duration_hr": 3},
    {"cat": "Vendor Quality Audit",        "priority": "P2", "required_types": ["QA", "FIE"], "required_cert": "ISO9001",   "duration_hr": 6},
    {"cat": "Inbound Material Inspection", "priority": "P2", "required_types": ["FIE", "WS"], "required_cert": None,        "duration_hr": 3},
    {"cat": "Regulatory Compliance Check", "priority": "P2", "required_types": ["QA"],        "required_cert": "HAZMAT",    "duration_hr": 5},
    {"cat": "Warehouse Exception",         "priority": "P3", "required_types": ["WS", "LC"],  "required_cert": None,        "duration_hr": 2},
    {"cat": "Routine Logistics Support",   "priority": "P3", "required_types": ["LC", "TP"],  "required_cert": None,        "duration_hr": 2},
]


def haversine_km(lat1, lon1, lat2, lon2):
    """Approximate km distance between two lat/lon points."""
    from math import radians, cos, sin, asin, sqrt
    R = 6371
    dlat = radians(lat2 - lat1)
    dlon = radians(lon2 - lon1)
    a = sin(dlat/2)**2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlon/2)**2
    return 2 * R * asin(sqrt(a))


def random_node():
    return random.choice(NODES)


def make_shift():
    """Return a shift window starting today."""
    today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    shift_starts = [6, 8, 10, 14]
    start_h = random.choice(shift_starts)
    duration = random.choice([8, 10, 12])
    start = today + timedelta(hours=start_h)
    end   = start + timedelta(hours=duration)
    return start.isoformat(), end.isoformat()


def generate_resources(n=80):
    resources = []
    for i in range(n):
        rtype = random.choice(RESOURCE_TYPES)
        node  = random_node()
        certs = list(set(RESOURCE_TYPE_CERTS[rtype] +
                         random.sample(CERTIFICATIONS, k=random.randint(0, 1))))
        shift_start, shift_end = make_shift()
        resources.append({
            "id":           f"R{i+1:03d}",
            "name":         f"{RESOURCE_TYPE_LABELS[rtype]} – {chr(65 + i % 26)}{i // 26 + 1}",
            "type":         rtype,
            "type_label":   RESOURCE_TYPE_LABELS[rtype],
            "home_node_id": node["id"],
            "home_node":    node["name"],
            "lat":          round(node["lat"] + random.uniform(-0.05, 0.05), 4),
            "lon":          round(node["lon"] + random.uniform(-0.05, 0.05), 4),
            "certifications": certs,
            "shift_start":  shift_start,
            "shift_end":    shift_end,
            "cost_per_km":  round(random.uniform(8.0, 25.0), 2),   # ₹ per km
            "capacity":     random.randint(1, 3),                    # max parallel assignments
            "available":    True,
            "current_load": 0,
        })
    return resources


def generate_requests(n=120):
    today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    requests = []
    for i in range(n):
        cat_info = random.choice(REQUEST_CATEGORIES)
        node     = random_node()
        # Request window: random start within business day
        req_start = today + timedelta(hours=random.randint(7, 18))
        req_end   = req_start + timedelta(hours=cat_info["duration_hr"])
        requests.append({
            "id":             f"REQ{i+1:04d}",
            "category":       cat_info["cat"],
            "priority":       cat_info["priority"],
            "required_type":  random.choice(cat_info["required_types"]),
            "required_cert":  cat_info["required_cert"],
            "node_id":        node["id"],
            "node_name":      node["name"],
            "lat":            round(node["lat"] + random.uniform(-0.02, 0.02), 4),
            "lon":            round(node["lon"] + random.uniform(-0.02, 0.02), 4),
            "start_time":     req_start.isoformat(),
            "end_time":       req_end.isoformat(),
            "duration_hr":    cat_info["duration_hr"],
            "description":    f"{cat_info['cat']} at {node['name']}",
            "sla_minutes":    30 if cat_info["priority"] == "P1" else 60 if cat_info["priority"] == "P2" else 120,
            "status":         "OPEN",
            "assigned_to":    None,
        })
    return requests


def save_json(obj, path):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as f:
        json.dump(obj, f, indent=2)
    print(f"  Saved {len(obj)} records → {path}")


if __name__ == "__main__":
    print("Generating FleetIQ sample data …")
    resources = generate_resources(80)
    requests  = generate_requests(120)
    nodes     = NODES

    save_json(nodes,     "data/sample/nodes.json")
    save_json(resources, "data/sample/resources.json")
    save_json(requests,  "data/sample/requests.json")

    # Pre-compute a distance matrix (resources × nodes) for the backend
    dist_matrix = {}
    for r in resources:
        dist_matrix[r["id"]] = {}
        for n in nodes:
            dist_matrix[r["id"]][n["id"]] = round(
                haversine_km(r["lat"], r["lon"], n["lat"], n["lon"]), 2
            )
    save_json(dist_matrix, "data/sample/distance_matrix.json")
    print("Done.")
