# FleetIQ – Supply Chain Mobile Resource Allocation Engine
## Use Case Storyline, Problem Statement & Approach

---

## 1. Executive Summary

**FleetIQ** is a decision-intelligence system that optimally assigns mobile supply chain resources — field inspection engineers, logistics coordinators, quality auditors, and warehouse supervisors — to incoming service requests across a multi-node industrial supply chain network spanning raw-material suppliers, manufacturing plants, warehouses, and distribution hubs.

The system compares three allocation algorithms (Greedy, Hungarian, and a custom Composite Score heuristic) and surfaces explainable assignments through an interactive web UI.

---

## 2. The Business Scenario

### Company: IndoSteel Logistics & Supply Pvt. Ltd.

IndoSteel operates a complex, multi-tier supply chain supporting integrated steel plants in Odisha and Jharkhand, with raw-material procurement from mines, logistics coordination across road/rail networks, and distribution to automotive OEM customers.

### The Challenge

The company maintains a **pool of ~80 mobile resources** (field personnel and vehicles) across 12 regional nodes. Every day, ~120–200 **service requests** arrive from:

- **Inbound side:** Mine dispatch quality checks, vendor audits, unloading supervision
- **Manufacturing side:** Process support, shift escalation coverage, inter-plant material transfers
- **Outbound side:** Customer shipment inspections, last-mile exception handling, 3PL coordination

Each request has a **location, time window, skill requirement, and priority tier**. Resources have **shift calendars, certifications, home depots, and capacity limits**.

The current manual dispatcher process leads to:
- 18–22% resource under-utilization
- 35+ minutes average assignment latency
- Priority-blind assignments (critical shipments delayed due to no tiering)
- No explainability — "why was this person assigned?" has no answer

### The Opportunity

Replace the manual dispatcher with an **intelligent allocation engine** that:
1. Runs multiple allocation strategies and picks the best
2. Respects hard constraints (certifications, shift windows, capacity)
3. Optimises soft constraints (minimize travel distance, balance workload, prioritize VIP requests)
4. Explains every decision

---

## 3. Domain Entities

### Resource Types
| Type | Code | Description |
|------|------|-------------|
| Field Inspection Engineer | FIE | Quality audits, acceptance testing |
| Logistics Coordinator | LC | Freight coordination, 3PL interface |
| Warehouse Supervisor | WS | Inbound/outbound supervision |
| Quality Auditor | QA | Compliance, regulatory checks |
| Transport Planner | TP | Route optimization, fleet dispatch |

### Request Categories
| Category | Priority |
|----------|----------|
| Critical Shipment Hold | P1 |
| Vendor Quality Audit | P2 |
| Inbound Material Inspection | P2 |
| Warehouse Exception | P3 |
| Routine Logistics Support | P3 |
| Customer Escalation | P1 |
| Regulatory Compliance Check | P2 |

### Node Locations (12 supply chain nodes)
- Mines/Raw Material: Barbil (Odisha), Noamundi (Jharkhand)
- Manufacturing: Kalinganagar Plant, Jamshedpur Plant
- Warehouses: Bhubaneswar Hub, Ranchi Hub, Kolkata Distribution Centre
- Logistics Yards: Paradip Port, Haldia Port, Raipur Rail Yard
- Customer Zones: Pune OEM Zone, Chennai OEM Zone

---

## 4. Problem Statement

> **Given a set of mobile supply chain resources at known locations with defined capabilities and shift schedules, and a stream of incoming service requests each specifying a location, time window, and skill requirements, build a system that assigns resources to requests optimally — minimising total cost (travel time + priority penalty) while satisfying hard constraints (availability, certification, capacity) and soft constraints (workload balance, proximity, cost efficiency).**

---

## 5. Constraint Specification

### Hard Constraints (must not be violated)
- **HC1 – Availability:** Resource must be free during the request time window
- **HC2 – Capability Match:** Resource type must match request requirement
- **HC3 – Single Assignment:** A resource can only serve one request at a time
- **HC4 – Shift Boundary:** Assignment must not cross the resource's shift end
- **HC5 – Certification:** Some P2/P1 requests require specific certifications (e.g., ISO 9001 auditor)

### Soft Constraints (optimise where possible)
- **SC1 – Proximity:** Prefer resources nearest to request location
- **SC2 – Workload Balance:** Avoid overloading individual resources
- **SC3 – Priority Weighting:** Earlier assignment of P1 requests
- **SC4 – Cost Efficiency:** Prefer lower per-km travel cost resources
- **SC5 – Continuity:** Where possible, assign same resource to repeat locations

---

## 6. Algorithmic Approach

### Algorithm 1 – Greedy Sequential
Process requests in descending priority order. For each request, evaluate all eligible resources and assign the one with the minimum composite cost (travel distance × priority weight). Fast (O(n·m)), sub-optimal globally but practical for real-time dispatch.

### Algorithm 2 – Hungarian (Kuhn-Munkres)
Batch-mode optimal assignment using the scipy implementation of the Hungarian algorithm. Builds an n×m cost matrix (requests × resources), solves for minimum total cost. Provably optimal for the linear assignment problem. O(n³).

### Algorithm 3 – Composite Score Heuristic (Custom)
Domain-informed scoring function combining:
- Normalised travel distance (30%)
- Priority urgency factor (40%)
- Workload balance score (20%)
- Certification bonus (10%)

Iterative improvement using 2-opt local search over the initial greedy solution.

---

## 7. Key Metrics Reported

| Metric | Definition |
|--------|------------|
| Assignment Rate | % of requests successfully assigned |
| Total Travel Cost | Sum of all travel distances (km) |
| Avg Response Time | Mean time from request to assignment |
| P1 Coverage | % of P1 requests assigned within SLA |
| Resource Utilization | Mean % of shift hours consumed |
| Unassigned Requests | Count of requests left unassigned |
| Cost per Assignment | Average travel cost per fulfilled request |
| Workload Gini | Inequality index across resource workload |

---

## 8. Decision Explanation (HITL)

Every assignment record carries:
- **Primary reason:** "Nearest certified resource with available shift capacity"
- **Score breakdown:** Travel=0.32, Priority=0.45, Balance=0.18, Cert=0.10
- **Alternatives considered:** Top 3 runner-up resources with their scores
- **Constraint violations avoided:** Which hard constraints screened out other candidates

---
