# ADR-001: Graph-Based Domain Model

**Status:** Accepted  
**Date:** 2026-03-29  
**Author:** Nicolas GOINEAU

---

## Context

Supply chain planning systems have historically modeled the world as **tables and cubes** — flat structures optimized for human-readable dashboards and batch SQL queries.

The fundamental limitation of this approach:

1. **Relationships are implicit** — a shortage is linked to a demand and a supply through SQL joins, not through explicit business relationships. You can't traverse the causality chain.
2. **Recalculation is global** — because dependencies are not modeled explicitly, any change requires recalculating everything.
3. **Explainability is absent** — when a KPI changes, the system can show you the new number but cannot walk you back through the chain of events that produced it.
4. **AI agents cannot navigate it** — a table of KPIs is not a machine-traversable structure. An agent querying "why is there a shortage at DC-East on April 15?" needs a graph, not a pivot table.

---

## Decision

**Ootils models the supply chain domain as a directed graph with typed nodes and typed edges.**

### Nodes
Each node represents a **typed business object** with its own properties:
- Reference objects: `Item`, `Location`, `Resource`, `Supplier`, `Policy`
- Demand objects: `ForecastDemand`, `CustomerOrderDemand`, `DependentDemand`, `TransferDemand`
- Supply objects: `OnHandSupply`, `PurchaseOrderSupply`, `WorkOrderSupply`, `TransferSupply`, `PlannedSupply`
- Constraint objects: `CapacityBucket`, `MaterialConstraint`
- Result objects: `ProjectedInventory`, `Shortage`

### Edges
Each edge represents a **named business relationship** with semantic meaning:

| Edge Type | Meaning |
|-----------|---------|
| `consumes` | A demand consumes a supply or inventory |
| `replenishes` | A supply replenishes projected inventory |
| `pegged_to` | A supply is allocated to a specific demand |
| `depends_on` | A node depends logically on another |
| `impacts` | A change in one node impacts another |
| `bounded_by` | A node is constrained by a constraint node |
| `governed_by` | A node is governed by a policy |
| `uses_capacity` | A supply order consumes capacity |

### Why typed edges (not just links)
The semantics of the relationship matter for:
- **Propagation** — which changes cascade through which edge types
- **Explainability** — "Order A *consumes* OnHand, which is *replenished* by PO-991, which is *delayed*"
- **Agent queries** — an agent can ask "show me all edges of type `impacts` downstream of this node"

---

## Consequences

**Positive:**
- Full causal traversal from any result back to its root causes
- Incremental recalculation by traversing only the dirty subgraph
- AI agents can navigate the graph natively via API
- Business relationships are explicit and auditable

**Negative / Trade-offs:**
- More complex to implement than a relational model
- Graph queries require careful indexing
- Mental shift required for developers coming from SQL-first backgrounds

**Mitigations:**
- Storage layer remains SQL (nodes and edges as tables) — we get SQL reliability with graph semantics at the application layer
- Graph traversal is implemented in the engine, not exposed as raw Cypher/Gremlin

---

## Alternatives Considered

### Option A: Pure relational model (rejected)
Standard tables with foreign keys. Simpler to implement but cannot support incremental propagation or native explainability. This is what every existing APS does — and why they all fail on causality.

### Option B: Native graph database (Neo4j / Neptune) (deferred)
Would provide native graph traversal but introduces significant operational complexity and couples the architecture to a specific technology. We start with SQL storage + application-layer graph semantics, and can migrate to a native graph DB in V2 if performance requires it.

### Option C: Event sourcing only (rejected)
Modeling everything as events with a projection layer. Elegant but makes real-time querying complex and doesn't naturally represent the supply chain as a network of objects.

---

## References
- [Architecture Overview — README.md](../README.md)
- [Stadtler & Kilger — Supply Chain Management and Advanced Planning (2015)](../BIBLIOGRAPHY.md)
- [Incremental execution of rule-based model transformation — Boronat (2020)](../BIBLIOGRAPHY.md)
