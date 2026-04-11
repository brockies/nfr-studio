---
project_id: "omnichannel_pos_004"
industry: "retail_omnichannel"
tech_stack: ["pos", "offline_mode", "edge_sync", "erp_integration"]
scale: "400_stores"
lessons:
  - "offline_first_is_hard"
  - "clock_skew_breaks_sync"
---

# Omnichannel POS + Ecommerce Integration (Anonymized)

## Context
In-store POS must operate during connectivity issues and sync inventory, pricing, and promotions with ecommerce and ERP.

## NFR Patterns That Mattered

### Availability & Resilience
- POS must support offline transactions for at least 30 minutes with conflict-safe sync.
- Sync must be resumable and idempotent; never duplicate sales or refunds.

### Data Quality
- Pricing/promotions must have a single source of truth and clear precedence rules to avoid customer disputes.

### Operability
- Store-level monitoring and alerting: detect sync lag, clock drift, and queue buildup.

## Lessons Learned
- Offline-first requires explicit conflict resolution and reconciliation playbooks.
- Clock skew causes subtle bugs; enforce NTP and validate client timestamps.

