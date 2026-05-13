"""
FleetIQ – FastAPI Backend
Run: uvicorn backend.main:app --reload --port 8000
"""
import time
import json
from pathlib import Path
from typing import List

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from backend.models.schemas import (
    Resource, ServiceRequest, Node,
    AllocationRequest, AllocationResult,
)
from backend.algorithms.allocator import run_allocation

app = FastAPI(
    title="FleetIQ – Supply Chain Resource Allocation Engine",
    description="Optimal assignment of mobile field resources to supply chain service requests.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

DATA_DIR = Path(__file__).parent.parent / "data" / "sample"


def load_json(filename: str):
    path = DATA_DIR / filename
    if not path.exists():
        return None
    with open(path) as f:
        return json.load(f)


# ── Health ────────────────────────────────────────────────────────────────────

@app.get("/health")
def health():
    return {"status": "ok", "service": "FleetIQ"}


# ── Data endpoints ─────────────────────────────────────────────────────────────

@app.get("/api/nodes", response_model=List[Node])
def get_nodes():
    data = load_json("nodes.json")
    if data is None:
        raise HTTPException(404, "Sample data not found. Run data/generate_sample_data.py first.")
    return data


@app.get("/api/resources", response_model=List[Resource])
def get_resources():
    data = load_json("resources.json")
    if data is None:
        raise HTTPException(404, "Sample data not found.")
    return data


@app.get("/api/requests", response_model=List[ServiceRequest])
def get_requests():
    data = load_json("requests.json")
    if data is None:
        raise HTTPException(404, "Sample data not found.")
    return data


# ── Allocation endpoint ───────────────────────────────────────────────────────

@app.post("/api/allocate", response_model=AllocationResult)
def allocate(payload: AllocationRequest):
    """
    Run a single allocation algorithm on the provided resources and requests.
    """
    if payload.algorithm not in ("greedy", "hungarian", "composite"):
        raise HTTPException(400, f"Unknown algorithm: {payload.algorithm}")

    t0 = time.perf_counter()
    result = run_allocation(
        resources=payload.resources,
        requests=payload.requests,
        algorithm=payload.algorithm,
    )
    elapsed_ms = round((time.perf_counter() - t0) * 1000, 2)
    result.run_time_ms = elapsed_ms
    return result


@app.post("/api/allocate/compare")
def compare_all(payload: AllocationRequest):
    """
    Run all three algorithms and return side-by-side results.
    """
    results = {}
    for algo in ("greedy", "hungarian", "composite"):
        t0 = time.perf_counter()
        result = run_allocation(
            resources=payload.resources,
            requests=payload.requests,
            algorithm=algo,
        )
        result.run_time_ms = round((time.perf_counter() - t0) * 1000, 2)
        results[algo] = result

    return {
        "greedy":    results["greedy"],
        "hungarian": results["hungarian"],
        "composite": results["composite"],
    }


# ── Default data allocation (uses sample files) ───────────────────────────────

@app.get("/api/allocate/default/{algorithm}")
def allocate_default(algorithm: str):
    """Run allocation on the bundled sample dataset."""
    resources_raw = load_json("resources.json")
    requests_raw  = load_json("requests.json")
    if resources_raw is None or requests_raw is None:
        raise HTTPException(404, "Sample data not found. Run data/generate_sample_data.py first.")

    resources = [Resource(**r) for r in resources_raw]
    requests  = [ServiceRequest(**r) for r in requests_raw]

    if algorithm not in ("greedy", "hungarian", "composite", "all"):
        raise HTTPException(400, f"algorithm must be greedy | hungarian | composite | all")

    if algorithm == "all":
        results = {}
        for algo in ("greedy", "hungarian", "composite"):
            t0 = time.perf_counter()
            r = run_allocation(resources, requests, algo)
            r.run_time_ms = round((time.perf_counter() - t0) * 1000, 2)
            results[algo] = r
        return results

    t0 = time.perf_counter()
    result = run_allocation(resources, requests, algorithm)
    result.run_time_ms = round((time.perf_counter() - t0) * 1000, 2)
    return result
