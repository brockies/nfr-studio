---
project_id: "grocery_platform_002"
industry: "grocery_ecommerce"
tech_stack: ["microservices", "kubernetes", "inventory", "slot_booking"]
scale: "20k_orders_day_peak"
lessons:
  - "inventory_consistency_over_latency"
  - "substitution_rules_complexity"
---

# Grocery Delivery Platform (Anonymized)

## Context
Online grocery ordering with delivery slot booking, substitutions, and real-time-ish inventory constraints.

## NFR Patterns That Mattered

### Data & Integration
- Inventory reservations must be strongly consistent for scarce items during peak demand (oversell is worse than latency).
- Substitution policy evaluation must be deterministic and auditable (why item A was substituted for B).

### Availability & Reliability
- Slot booking needs strict concurrency control and idempotency to avoid double-booking.
- Background pick/pack workflows must tolerate partial failures and retries without duplicates.

### Operability
- Traceability: correlate order, reservation, slot, payment, and fulfillment events across services.

## Lessons Learned
- Inventory "eventual" consistency caused customer trust issues; invest early in reservation semantics.
- Slot booking is effectively a critical "inventory" domain.
- Observability must be designed, not bolted on, due to distributed decisioning.

