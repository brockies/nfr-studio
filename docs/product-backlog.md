# NFR Studio Product Backlog

## Product Direction

NFR Studio should evolve from an NFR generation tool into an architecture assurance copilot.

Core proposition:

> Tell me not just what requirements I need, but what I will need to prove later.

This means the product should help teams:

- define relevant NFRs
- prioritise them
- map them to applicable frameworks
- identify the controls implied by those NFRs
- define the evidence, owners, and validation activities needed later

## Outcome Goals

### Near-Term

- Make compliance outputs more actionable than a framework checklist.
- Help teams identify missing evidence early.
- Improve trust by showing why a framework is or is not relevant.

### Mid-Term

- Support different framework packs and industry profiles.
- Reduce duplicated compliance work through crosswalks and shared artefacts.
- Make outputs useful for architects, compliance teams, and delivery teams.

### Longer-Term

- Provide traceable assurance cases.
- Track evidence readiness over time.
- Support AI governance and audit-readiness workflows as a first-class product feature.

## Assumptions

- The current pipeline already generates NFRs, scoring, test criteria, remediation, and compliance mapping.
- The first backlog increments should extend existing outputs before adding major new workflow complexity.
- The compliance tab is currently prompt-driven, so some early wins can be delivered without major UI or data model redesign.

## MVP Backlog

### Epic MVP-1: Evidence Planner

Goal: For important NFRs, explain what must be evidenced later.

#### Story MVP-1.1

As an architect, I want each critical or high-priority NFR to include an evidence plan so I can turn generated outputs into delivery and governance actions.

Acceptance criteria:

- Each critical or high-priority NFR can be associated with one or more evidence items.
- Each evidence item includes:
  - control theme
  - evidence required
  - suggested owner
  - validation approach
  - suggested delivery stage
- The output clearly separates requirement text from proof expectations.

#### Story MVP-1.2

As a compliance lead, I want evidence items to be phrased as concrete artefacts so I can identify what documentation or operational records are missing.

Acceptance criteria:

- Evidence suggestions use tangible artefact language such as policy, runbook, test report, decision log, approval record, access review, DPIA, model card, or incident log.
- Evidence suggestions avoid vague wording such as "have governance" without naming a likely artefact.
- Evidence suggestions can be produced in markdown output without breaking existing run output formats.

#### Story MVP-1.3

As a delivery lead, I want suggested owners for evidence items so I can assign follow-up work quickly.

Acceptance criteria:

- Suggested owners use role-based labels such as Security, Platform, Engineering Lead, Product, Data Protection, or AI Governance.
- Owners are recommendations rather than hard-coded mandates.
- Where ownership is unclear, the output states that clarification is needed.

### Epic MVP-2: Framework Applicability

Goal: Make framework mapping more targeted and defensible.

#### Story MVP-2.1

As a user, I want each framework to be labelled as applicable, potentially applicable, or not applicable so I can understand scope instead of seeing a generic checklist.

Acceptance criteria:

- Each framework listed in the compliance output has an applicability label.
- Each label includes a short rationale grounded in the system description.
- The output avoids presenting all frameworks as equally relevant by default.

#### Story MVP-2.2

As an architect, I want the system to explain why a framework applies so I can defend those choices in review discussions.

Acceptance criteria:

- Rationale references relevant system traits such as AI usage, payments, personal data, resilience obligations, or sector context.
- Where applicability is inferred from incomplete input, the output states that explicitly.
- The output does not overstate legal applicability when the context is weak.

### Epic MVP-3: Proof Gaps

Goal: Highlight where the team has a requirement but no obvious proof plan.

#### Story MVP-3.1

As a project team, I want proof gaps called out explicitly so we can reduce audit and delivery surprises.

Acceptance criteria:

- A dedicated "Proof Gaps" section is included in the compliance or remediation output.
- The section highlights cases where an NFR exists but there is no clear:
  - evidence item
  - owner
  - validation method
  - framework linkage
- Proof gaps are prioritised toward critical and high-priority NFRs first.

### Epic MVP-4: NFR-to-Control-to-Evidence Matrix

Goal: Provide a compact operational view of what must be implemented and proven.

#### Story MVP-4.1

As a user, I want a matrix showing NFR to framework to control theme to evidence so I can quickly understand downstream obligations.

Acceptance criteria:

- A markdown table is produced for relevant NFRs.
- The table contains at minimum:
  - NFR ID
  - framework
  - control theme
  - evidence required
  - owner
- The table is readable in existing markdown rendering in the app.

### Epic MVP-5: Framework Expansion

Goal: Make AI governance first-class in the compliance workflow.

#### Story MVP-5.1

As a user evaluating AI-enabled systems, I want AI-specific frameworks included in compliance mapping so the output reflects modern governance expectations.

Acceptance criteria:

- Compliance mapping considers:
  - EU AI Act
  - ISO/IEC 42001
  - NIST AI RMF
- Existing framework handling for ISO 27001, SOC 2, GDPR / UK GDPR, PCI DSS, and NIS2 remains intact.
- Frameworks are still only mapped where relevant to the described system.

## Phase 2 Backlog

### Epic P2-1: Framework Packs

Goal: Allow users to apply targeted framework bundles instead of one universal set.

#### Story P2-1.1

As a user, I want selectable framework packs so the analysis is aligned to my context.

Acceptance criteria:

- The product supports named packs such as:
  - Core SaaS
  - AI Product
  - Ecommerce
  - Fintech
  - Health
  - Public Sector
- Each pack preselects a curated framework set.
- Users can override the selected pack or adjust individual frameworks.

#### Story P2-1.2

As a product team, I want framework packs to be configurable so we can evolve them without reworking the whole pipeline.

Acceptance criteria:

- Framework pack definitions are externalised into maintainable configuration or structured knowledge base content.
- A framework can appear in multiple packs.
- Changes to packs do not require prompt rewrites across unrelated agents.

### Epic P2-2: Industry Profiles

Goal: Improve relevance and reduce weak generic outputs.

#### Story P2-2.1

As a user, I want to choose an industry profile so the app can bias toward relevant NFRs, risks, and evidence.

Acceptance criteria:

- The product supports initial profiles such as:
  - SaaS
  - AI SaaS
  - Ecommerce
  - Fintech
  - Healthtech
  - Public Sector
- Profiles influence:
  - likely frameworks
  - likely NFR themes
  - likely evidence artefacts
- The profile can be overridden by user-supplied context.

### Epic P2-3: Evidence Crosswalks

Goal: Show that one artefact can satisfy several frameworks.

#### Story P2-3.1

As a compliance lead, I want shared evidence crosswalks so teams can avoid duplicating documentation effort.

Acceptance criteria:

- The output can show one evidence artefact linked to multiple frameworks or control themes.
- Crosswalks clearly distinguish shared artefacts from framework-specific artefacts.
- Crosswalk output remains understandable in markdown and future UI views.

### Epic P2-4: Confidence and Assumption Scoring

Goal: Make the system more trustworthy by exposing weak assumptions.

#### Story P2-4.1

As a user, I want confidence indicators on compliance conclusions so I know where more stakeholder clarification is needed.

Acceptance criteria:

- The system can flag low-confidence mappings.
- Confidence is influenced by missing context, legal ambiguity, or weak evidence in the system description.
- The output explains what additional information would improve confidence.

### Epic P2-5: Stakeholder Views

Goal: Make the same analysis usable by different audiences.

#### Story P2-5.1

As an architect, compliance lead, delivery lead, or executive sponsor, I want a tailored view of the same run so I can focus on what matters to my role.

Acceptance criteria:

- The product supports role-oriented views for:
  - architecture
  - security/compliance
  - delivery planning
  - executive summary
- Each view reuses the same underlying run outputs.
- No role view invents new requirements not present in the main run context.

### Epic P2-6: Delivery Governance and RAID

Goal: Support healthier product delivery without mixing governance tracking into the core backlog.

#### Story P2-6.1

As a product team, I want a separate RAID log so risks, assumptions, issues, and dependencies are visible without cluttering the feature backlog.

Acceptance criteria:

- The product repo includes a separate RAID document rather than embedding RAID entries directly into the backlog.
- RAID entries can capture:
  - risks
  - assumptions
  - issues
  - dependencies
- Initial RAID content reflects real delivery concerns such as model variability, privacy posture, project-scoped retrieval, external provider dependence, and workflow/orchestration complexity.
- RAID setup is scheduled after an initial round of user testing so delivery governance reflects observed product and user risks, not only design assumptions.

## Longer-Term Backlog

### Epic LT-1: Assurance Case Mode

Goal: Turn outputs into a defendable structured argument.

#### Story LT-1.1

As an architecture or governance team, I want an assurance case output so I can connect design claims to evidence and unresolved risks.

Acceptance criteria:

- The system can produce:
  - claim
  - argument
  - evidence
  - gap
  - next action
- Assurance cases can reference existing NFR IDs and compliance outputs.
- The structure is suitable for review meetings and audit preparation.

### Epic LT-2: AI Governance Depth

Goal: Make AI-enabled system assessments much more defensible.

#### Story LT-2.1

As a team building or using AI systems, I want AI governance-specific analysis so that model risk and oversight obligations are not reduced to generic security controls.

Acceptance criteria:

- AI governance output can address:
  - model inventory
  - third-party model dependence
  - human oversight
  - prompt injection and misuse risks
  - monitoring and drift
  - model or prompt change control
  - AI literacy
  - incident handling for harmful outputs
- The output is only produced where AI usage is relevant.

### Epic LT-3: Evidence Lifecycle Tracking

Goal: Move from one-off analysis to ongoing readiness management.

#### Story LT-3.1

As a team preparing for review or audit, I want evidence items to have lifecycle states so I can track readiness over time.

Acceptance criteria:

- Evidence items can carry statuses such as:
  - planned
  - in progress
  - collected
  - stale
  - missing
- Evidence items can store an owner and review date.
- Status tracking is available without losing the original generated recommendation.

### Epic LT-4: Artefact Ingestion and Traceability

Goal: Ground analysis in real project artefacts.

#### Story LT-4.1

As a user, I want to upload real artefacts and have them linked to NFRs and framework areas so the system can move from planning support to evidence-assisted assessment.

Acceptance criteria:

- Users can upload artefacts such as:
  - architecture diagrams
  - policies
  - ADRs
  - test reports
  - runbooks
- The system can summarise artefacts and propose traceability links to:
  - NFRs
  - control themes
  - frameworks
  - evidence items
- Suggested links are clearly marked as inferred until confirmed.

### Epic LT-5: Readiness Scoring

Goal: Provide a concise management signal without hiding detail.

#### Story LT-5.1

As a delivery or governance lead, I want readiness scores so I can quickly see where the programme is strong or exposed.

Acceptance criteria:

- The product can produce separate readiness views for:
  - design readiness
  - operational readiness
  - audit readiness
  - AI governance readiness
- Scores are supported by transparent rationale and cited gaps.
- Scores never appear without explanation.

## Suggested Delivery Sequence

### First Release

- MVP-1 Evidence Planner
- MVP-2 Framework Applicability
- MVP-3 Proof Gaps
- MVP-4 NFR-to-Control-to-Evidence Matrix
- MVP-5 Framework Expansion

### Second Release

- P2-1 Framework Packs
- P2-2 Industry Profiles
- P2-3 Evidence Crosswalks
- P2-4 Confidence and Assumption Scoring
- P2-5 Stakeholder Views
- P2-6 Delivery Governance and RAID

### Strategic Release

- LT-1 Assurance Case Mode
- LT-2 AI Governance Depth
- LT-3 Evidence Lifecycle Tracking
- LT-4 Artefact Ingestion and Traceability
- LT-5 Readiness Scoring

## Recommended First Build Slice

If only one slice is built next, prioritise:

1. Evidence Planner for critical and high-priority NFRs
2. Proof Gaps section
3. Framework applicability labels
4. NFR-to-Control-to-Evidence matrix

Reason:

- It strengthens the current product direction without needing a major workflow redesign.
- It creates immediate value for architecture, delivery, and compliance users.
- It provides a clearer differentiation story than adding more frameworks alone.
