---
project_id: "subscription_box_005"
industry: "subscription_ecommerce"
tech_stack: ["recurring_billing", "crm", "batch_jobs"]
scale: "250k_subscribers"
lessons:
  - "batch_cutoff_times_define_user_expectations"
  - "billing_idempotency_everywhere"
---

# Subscription Box Ecommerce (Anonymized)

## Context
Recurring billing with monthly fulfillment cycles, customer preference windows, and batch-driven fulfillment planning.

## NFR Patterns That Mattered

### Reliability
- Billing operations must be idempotent for retries (charges, refunds, adjustments).
- Fulfillment batch pipelines must be resumable and restart-safe.

### Performance
- Batch processing must complete within strict cutoffs to meet warehouse windows.

### Security
- Strong controls around billing adjustments and refund permissions.

## Lessons Learned
- Users experience "deadlines" even if the UI says otherwise; define cutoffs explicitly.
- Retry storms happen; protect payment providers with backoff and circuit breakers.

