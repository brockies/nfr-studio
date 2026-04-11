---
project_id: "marketplace_003"
industry: "multi_vendor_marketplace"
tech_stack: ["payments", "payouts", "fraud", "event_driven"]
scale: "5m_users"
lessons:
  - "payout_reconciliation_is_product"
  - "fraud_signals_need_low_latency"
---

# Multi-Vendor Marketplace (Anonymized)

## Context
Marketplace with vendor onboarding, split payments, payouts, refunds, and disputes.

## NFR Patterns That Mattered

### Security & Compliance
- Strong audit trails for payout calculations, refunds, and fee changes.
- Least-privilege access to financial operations; dual control for payout configuration changes.

### Data & Integration
- Exactly-once-ish processing for money-moving events using idempotency keys and reconciliation jobs.
- Maintain an immutable ledger of financial events (append-only) as the system of record.

### Performance
- Fraud screening signals must be computed within the checkout latency budget.

## Lessons Learned
- Reconciliation and reporting are user-facing features, not just ops tasks.
- Event-driven pipelines need backpressure and replay strategy from day one.

