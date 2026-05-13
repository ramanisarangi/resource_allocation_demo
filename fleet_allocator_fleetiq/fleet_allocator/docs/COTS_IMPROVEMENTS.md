# Improvement Options: Commercial Off-the-Shelf Tools & Solvers

## FleetIQ – Path to Production-Grade Capability

---

## 1. Optimisation Solvers

### Gurobi (Most Recommended)
- **What:** Best-in-class MIP/LP solver with Python API (`gurobipy`)
- **Replaces:** SciPy `linear_sum_assignment`
- **Value:** Handles large-scale (10,000+ resources × requests), vehicle routing extensions (VRPTW), multi-shift planning, robust uncertainty models, parallel branch-and-bound
- **License:** Free academic; commercial licence required for production
- **Integration:** Replace `allocate_hungarian()` with a `gurobipy` Model, add integer variables for multi-assignment, time-window constraints as linear inequalities
- **Expected gain:** 20–35% cost reduction over Greedy on large instances; solutions proven optimal

### Google OR-Tools (Free, Open Source)
- **What:** Google's open-source constraint programming and routing library
- **Replaces:** All three algorithms
- **Value:** Vehicle Routing Problem (VRP), Capacitated VRP, VRP with Time Windows (VRPTW) — all directly applicable to the field-resource dispatch problem
- **Integration:** Use `ortools.constraint_solver` routing module; model resources as "vehicles", requests as "nodes", depot as home node
- **Expected gain:** Handles real-world scale (1,000+ nodes); optimality gap typically < 2% with default settings

### PuLP + CBC (Already in stack)
- **What:** Python LP modelling layer over CBC open-source solver
- **Value:** Sufficient for medium instances (< 500 requests); good for experimentation and prototyping
- **Integration:** Already in Ramani's known stack; extend current cost matrix to full Mixed Integer Program (MIP)

---

## 2. Supply Chain Planning Platforms

### Palantir Foundry (Ramani's certified platform)
- **What:** Enterprise data + AI platform with Contour (analysis), Quill (reports), Workshop (apps), AIP (AI agents)
- **FleetIQ integration:**
  - Ingest resource and request data via Foundry Pipelines (REST or Kafka)
  - Run allocation algorithms as Foundry Transforms (Python code blocks)
  - Build the dispatch UI as a Workshop application
  - Add AIP Agent to handle natural-language overrides ("reassign all P1 requests in Paradip to available QA resources")
- **Value:** Native audit trail, role-based access control, lineage — production-ready from day one
- **Licence:** Enterprise; Ramani already holds Solution Architect and Developer certifications

### o9 Solutions / Blue Yonder / Kinaxis
- **What:** Enterprise Integrated Business Planning (IBP) platforms
- **Value:** Pre-built supply chain network models, constraint-aware planning, what-if scenario capability
- **Integration path:** Export FleetIQ assignments as constraint input to the IBP demand planning module

### SAP IBP (Integrated Business Planning)
- **What:** SAP's cloud-based supply chain planning suite
- **Value:** Native integration with SAP ERP (material master, vendor master, plant data) — relevant if IndoSteel runs SAP
- **Integration:** Expose FleetIQ as a BTP (Business Technology Platform) service; consume resource/request data from S/4HANA

---

## 3. Geospatial & Routing Services

### Open Source (Current Stack)
- **Leaflet + OpenStreetMap:** Map rendering (already implemented)
- **OSRM (Open Source Routing Machine):** Self-hosted routing engine — replace haversine with real road/rail network distance (run locally via Docker)
- **Valhalla:** Alternative routing engine with truck routing support (relevant for heavy logistics)

### Commercial (When Scale Demands It)
- **HERE Routing API:** Real-time traffic-aware routing, fleet-specific (truck, hazmat)
- **Google Maps Platform:** Distance Matrix API for batch distance lookups
- **Integration:** Replace `haversine_km()` with an API call; cache results in a local Redis/SQLite store

---

## 4. ML-Based Allocation

### XGBoost / LightGBM (Supervised Learning)
- **Approach:** Train on historical assignment + outcome data; predict "assignment quality score" for each resource-request pair
- **Features:** Distance, priority, cert match, time of day, historical SLA performance, resource utilisation trend
- **Integration:** Replace `compute_cost()` with model `.predict_proba()`; greedy layer picks max-score feasible resource
- **Tooling:** Azure ML (Ramani's stack), MLflow for tracking, Docker for serving

### Reinforcement Learning (Advanced)
- **Approach:** Model as a Sequential Decision Process; train a policy to dispatch resources
- **Frameworks:** Ray RLlib, Stable Baselines3
- **State:** Resource locations, loads, shift times; **Action:** Assign resource R to request Q; **Reward:** −travel_cost + priority_bonus − SLA_penalty
- **Suitable when:** 500+ requests/day with complex dynamics (cancellations, real-time arrivals, resource attrition)

### Azure ML AutoML (Ramani's known platform)
- **Approach:** Automated feature engineering and model selection on allocation history
- **Integration:** Azure ML SDK → Docker → FastAPI inference endpoint → FleetIQ backend

---

## 5. Monitoring & Observability

| Tool | Use |
|------|-----|
| Power BI / Tableau | KPI dashboards for operations team (Ramani's stack) |
| MLflow | Experiment tracking for algorithm tuning |
| Prometheus + Grafana | API latency and resource utilisation monitoring |
| Apache Kafka | Event streaming for real-time request ingestion |
| Redis | Assignment cache; prevent duplicate dispatch |

---

## 6. Recommended Upgrade Path

```
Phase 0 (Current): FleetIQ OSS – React + FastAPI + SciPy
       ↓
Phase 1 (Month 3): Add OR-Tools VRPTW routing; OSRM real-distance
       ↓
Phase 2 (Month 6): Palantir Foundry integration; Workshop UI; AIP agent
       ↓
Phase 3 (Month 9): Gurobi MIP for batch planning; Azure ML for predictive scoring
       ↓
Phase 4 (Year 2): Reinforcement Learning policy for real-time dynamic dispatch
```

---

## Cost-Benefit Summary

| Option | Effort | Cost | Expected Gain |
|--------|--------|------|---------------|
| OR-Tools VRPTW | 2 weeks | Free | +15% cost reduction, handles real routing |
| OSRM routing | 3 days | Free (self-hosted) | +8% accuracy vs. haversine |
| Palantir Foundry | 4–6 weeks | Enterprise licence | Enterprise governance, HITL, audit trail |
| Gurobi MIP | 2–3 weeks | Commercial licence | Provably optimal large-scale planning |
| Azure ML scoring | 4 weeks | Pay-per-use | Learned dispatch patterns from history |

---
