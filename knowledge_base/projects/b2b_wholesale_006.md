---
project_id: "b2b_wholesale_006"
industry: "b2b_wholesale_ecommerce"
tech_stack: ["catalog_pricing", "erp", "bulk_orders", "sso"]
scale: "10k_buyers"
lessons:
  - "pricing_rules_need_explainability"
  - "bulk_order_ux_needs_performance_budgets"
---

# B2B Wholesale Ordering Portal (Anonymized)

## Context
B2B buyers place large bulk orders with complex contract pricing, approvals, and ERP integration.

## NFR Patterns That Mattered

### Usability & Accessibility
- Bulk ordering flows must remain responsive even with thousands of line items.
- Keyboard navigation and accessible tables are required for power users.

### Data & Integration
- ERP integration must have clear retry semantics and human-readable failure reporting.

### Security
- SSO + RBAC for buyer organizations; audit access to price lists and contracts.

## Lessons Learned
- "Why is this price applied?" is a first-class feature (explainability).
- Performance budgets should be defined for bulk import and cart operations.

