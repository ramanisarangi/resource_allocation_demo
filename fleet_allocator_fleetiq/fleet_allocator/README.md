# FleetIQ – Supply Chain Resource Allocation Engine

An intelligent decision system that optimally assigns mobile field resources (inspection engineers, logistics coordinators, quality auditors) to supply chain service requests across a multi-node industrial network.

---
## Use Case

**IndoSteel Logistics & Supply Pvt. Ltd.** operates a complex supply chain across 12 nodes (mines, plants, warehouses, ports) in eastern India. Each day, 120–200 service requests arrive from field operations requiring mobile resources with specific capabilities and certifications. FleetIQ replaces manual dispatch with three competing allocation algorithms, surfacing explainable, optimised assignments through an interactive web UI.

**See:** [`docs/USE_CASE.md`](docs/USE_CASE.md) for full business context and problem statement.

---
## Architecture

```
fleetiq/
├── backend/
│   ├── main.py                    # FastAPI application
│   ├── models/schemas.py          # Pydantic data models
│   └── algorithms/allocator.py   # Greedy, Hungarian, Composite algorithms
├── frontend/
│   └── src/
│       ├── App.js                 # React application (map + charts + table)
│       └── App.css                # Dark-theme styles
├── data/
│   ├── generate_sample_data.py    # Sample data generator (80 resources, 120 requests)
│   ├── generate_test_data.py      # Test fixture generator (4 boundary scenarios)
│   └── sample/                    # Generated JSON files (after running generator)
│       ├── nodes.json
│       ├── resources.json
│       ├── requests.json
│       └── distance_matrix.json
├── tests/
│   └── test_allocator.py          # Pytest suite (35+ test cases)
├── docs/
│   ├── USE_CASE.md                # Business storyline & problem statement
│   ├── ALGORITHM_COMPARISON.md   # Analytical write-up
│   └── COTS_IMPROVEMENTS.md      # Commercial improvement options
└── requirements.txt
```

---
## Prerequisites

- Python 3.10+
- Node.js 18+ and npm
- Git (to clone)

No paid services, API keys, or cloud accounts required.

---
## Setup Instructions

### Step 1 – Clone & set up Python environment

```bash
cd fleet_allocator

# Create virtual environment
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate

# Install Python dependencies
pip install -r requirements.txt
```

### Step 2 – Generate sample data

```bash
cd data
python generate_sample_data.py     # Creates data/sample/*.json
python generate_test_data.py       # Creates data/test/*.json
cd ..
```

Verify the output:
```
data/sample/nodes.json             # 12 supply chain nodes
data/sample/resources.json         # 80 mobile resources
data/sample/requests.json          # 120 service requests
data/sample/distance_matrix.json   # Pre-computed distances
```

### Step 3 – Start the FastAPI backend

```bash
# From project root
uvicorn backend.main:app --reload --port 8000
```

Verify: open http://localhost:8000/docs in your browser — you should see the Swagger UI.

Quick test:
```bash
curl http://localhost:8000/health
# → {"status":"ok","service":"FleetIQ"}

curl http://localhost:8000/api/allocate/default/greedy | python -m json.tool | head -50
```

### Step 4 – Start the React frontend

Open a **new terminal**:

```bash
cd frontend
npm install
npm start
```

The browser opens at http://localhost:3000

---
## Using the UI

| Feature | Where |
|---------|-------|
| Select algorithm | Control bar → Greedy / Hungarian / Composite |
| Run allocation | Click **▶ Run** |
| Compare all 3 | Click **⚖ Compare All** |
| Map view | Tab → 🗺 Map View (nodes, resources, assignment lines) |
| Assignment details | Tab → 📋 Assignments (click ▼ for explanation + alternatives) |
| Algorithm comparison | Tab → ⚖ Algorithm Compare (bar chart + radar) |
| Toggle lines on map | ☑ Show lines checkbox |

**Map legend:**
- Large circles = supply chain nodes (coloured by type: mine, plant, warehouse…)
- Small circles = resources (coloured by type: FIE, LC, WS, QA, TP)
- Lines = assignments (red=P1, orange=P2, grey=P3)

---
## Running Tests

```bash
# From project root, with virtual environment active
cd data && python generate_test_data.py && cd ..

pytest tests/ -v
```

Expected output:
```
tests/test_allocator.py::TestHaversine::test_same_point_is_zero PASSED
tests/test_allocator.py::TestHaversine::test_known_distance_bbsr_to_kolkata PASSED
...
tests/test_allocator.py::TestAlgorithmComparison::test_all_algorithms_run PASSED
tests/test_allocator.py::TestWithFixtures::test_fixture_01_perfect_match PASSED
...
35 passed in 2.4s
```

Run a specific test class:
```bash
pytest tests/test_allocator.py::TestFeasibility -v
pytest tests/test_allocator.py::TestAlgorithmComparison -v
```

---
## API Reference

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/health` | Health check |
| GET | `/api/nodes` | All supply chain nodes |
| GET | `/api/resources` | All resources |
| GET | `/api/requests` | All service requests |
| GET | `/api/allocate/default/{algo}` | Run on sample data; algo = greedy\|hungarian\|composite\|all |
| POST | `/api/allocate` | Run on custom payload |
| POST | `/api/allocate/compare` | Run all 3 on custom payload |

Interactive docs: http://localhost:8000/docs

---
## Algorithms

| Algorithm | Strategy | Complexity | Best For |
|-----------|----------|------------|----------|
| **Greedy** | Priority-ordered sequential, min-cost pick | O(n·m) | Real-time streaming dispatch |
| **Hungarian** | Global optimal via linear assignment | O(n³) | Batch planning, cost minimisation |
| **Composite** | Multi-factor score + 2-opt improvement | O(n·m·k) | Multi-objective + explainability |

**Constraints enforced:**
- HC1 – Resource availability
- HC2 – Type match (FIE/LC/WS/QA/TP)
- HC3 – Capacity (max parallel assignments per resource)
- HC4 – Shift boundary (request within shift window)
- HC5 – Certification match (ISO9001, HAZMAT, etc.)
- SC1–SC5 – Soft constraints (proximity, balance, priority weighting)

---
## Documentation

| File | Contents |
|------|----------|
| `docs/USE_CASE.md` | Full business scenario, data model, constraints |
| `docs/ALGORITHM_COMPARISON.md` | Analytical comparison with observed results |
| `docs/COTS_IMPROVEMENTS.md` | Gurobi, OR-Tools, Palantir Foundry, Azure ML paths |

---
## Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend | Python 3.10+, FastAPI, Pydantic v2, SciPy, NumPy |
| Frontend | React 18, React-Leaflet, Recharts, Lucide-React |
| Maps | Leaflet.js + OpenStreetMap (free, no API key) |
| Testing | Pytest |
| Solver | SciPy `linear_sum_assignment` (Hungarian) |

---
## End of Document
