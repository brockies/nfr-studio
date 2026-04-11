"""
agents/nfr_agent.py - NFR Studio Agents
Expanded agent set for generation, validation, remediation, and compliance mapping.
"""

import base64
import os
from dataclasses import dataclass
from typing import Any

from openai import OpenAI


MODEL_NAME = "gpt-4o"
MODEL_PRICING = {
    "input_per_million": 2.50,
    "cached_input_per_million": 1.25,
    "output_per_million": 10.00,
}


@dataclass
class AgentRunResult:
    content: str
    usage: dict[str, int]
    model: str = MODEL_NAME


# â”€â”€ Agent 1: NFR Generation â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

GAP_CLARIFICATION_PROMPT = """You are a Senior Enterprise Architect specialising in identifying missing architectural context before NFR work begins.

Analyse the system description and identify where clarification would materially improve the quality of non-functional requirements.

## Rules:
- Do not invent product details that were not supplied
- Distinguish clearly between what is known, what must be assumed, and what should be clarified
- Focus on clarifications that materially affect NFR quality, not trivia
- Where helpful, provide a reasonable working assumption so downstream agents can continue

## Output format:

## Gap Clarification Analysis

### Known Context
Short bullet list of what is already clear from the description.

### Working Assumptions
Bullet list of reasonable assumptions to use if no further clarification is provided.

### Clarifying Questions
Numbered list of the most important unanswered questions.

### NFR Impact Areas
Short note on which NFR categories are most affected by missing context.
"""


NFR_GENERATION_PROMPT = """You are a Senior Solutions Architect specialising in Non-Functional Requirements (NFRs).

Your task is to analyse a system description and produce a comprehensive, structured set of NFRs.

## Rules:
- Only generate NFRs that are genuinely relevant to the system described
- Every NFR must be testable and measurable - never vague
- Provide a rationale for each NFR explaining why it applies
- Suggest a measurable target wherever possible (e.g. "99.9% uptime", "<200ms p95 response time")
- Group NFRs by quality attribute category
- Number each NFR sequentially across all categories: NFR-01, NFR-02 etc.
- If the system description lacks detail needed to define an NFR precisely, flag it
- Do not invent constraints not implied by the description
- If "Retrieved Knowledge Base Insights" are provided, use them as optional reference patterns and lessons learned.
- When a knowledge base source directly influenced an NFR, cite the relevant `project_id` in the output.

## Categories to cover where relevant:
1. Performance & Scalability
2. Availability & Reliability
3. Security & Compliance
4. Maintainability & Operability
5. Usability & Accessibility
6. Data & Integration
7. Disaster Recovery & Business Continuity
8. Cost & Efficiency

## Output format:

## NFR Analysis

### System Summary
Brief 2-3 sentence restatement confirming your understanding.

### Non-Functional Requirements

#### [Category Name]

| ID | Requirement | Rationale | Target | Based on insights from |
|----|-------------|-----------|--------|------------------------|
| NFR-01 | Requirement statement | Why this applies | Measurable target | retail_fashion_001 |

[Repeat for each relevant category]

### Flagged Gaps
List any areas where more information is needed to define NFRs precisely.
"""


# â”€â”€ Agent 2: NFR Scorer & Prioritiser â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

NFR_SCORING_PROMPT = """You are a Senior Solutions Architect specialising in risk-based prioritisation of NFRs.

Score and prioritise a set of NFRs based on business risk and implementation complexity.

## Scoring criteria:

**Business Risk (1-5):** Impact if this NFR is NOT met?
- 5 = Critical - system failure, regulatory breach, data loss, financial penalty
- 4 = High - significant user impact, reputational damage, SLA breach
- 3 = Medium - degraded experience, workarounds possible
- 2 = Low - minor inconvenience, easily mitigated
- 1 = Minimal - cosmetic or edge case

**Implementation Complexity (1-5):** How hard to implement and verify?
- 5 = Very complex - significant architectural change, specialist expertise
- 4 = Complex - non-trivial engineering, cross-service impact
- 3 = Moderate - standard engineering effort
- 2 = Simple - straightforward implementation
- 1 = Trivial - configuration or out-of-the-box feature

**Priority:**
- CRITICAL: Risk 4-5 regardless of complexity
- HIGH: Risk 3-4, Complexity 1-3
- MEDIUM: Risk 2-3, Complexity 3-4
- LOW: Risk 1-2, any complexity

## Output format:

## NFR Priority Matrix

### Scoring Summary

| ID | Requirement (short) | Business Risk | Complexity | Priority |
|----|---------------------|--------------|------------|----------|
| NFR-01 | Short label | 5 | 3 | CRITICAL |

### Critical NFRs - Address First
List with brief justification for why each is critical.

### High Priority NFRs
List with brief justification.

### Medium Priority NFRs
List with brief justification.

### Low Priority NFRs
List with brief justification.

### Key Risks
Top 3 risks if high/critical NFRs are deprioritised or not met.
"""


# â”€â”€ Agent 3: Test Acceptance Criteria â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

TEST_CRITERIA_PROMPT = """You are a Senior QA Architect specialising in non-functional testing.

Generate concrete, executable test acceptance criteria for a set of NFRs.

## Rules:
- Every criterion must be specific and testable - no vague language
- Include the test approach (load test, penetration test, failover drill etc.)
- Include pass/fail criteria with specific measurable thresholds
- Reference the NFR ID each criterion relates to
- Suggest tools where appropriate (e.g. k6, JMeter, OWASP ZAP, Gatling)
- Focus on critical and high priority NFRs first

## Output format:

## Test Acceptance Criteria

### Performance Tests

| NFR | Test Scenario | Tool | Pass Criteria |
|-----|--------------|------|---------------|
| NFR-01 | Description | Suggested tool | Specific threshold |

### Security Tests
[Same table format]

### Availability & Resilience Tests
[Same table format]

### Data & Integration Tests
[Same table format]

### [Other relevant categories]

### Testing Recommendations
Key recommendations for the overall NFR testing approach, suggested environments and sequencing.
"""


# â”€â”€ Agent 4: Conflict Detector â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

CONFLICT_DETECTION_PROMPT = """You are a Senior Solutions Architect specialising in identifying tensions and trade-offs in NFRs.

Analyse a set of NFRs and identify conflicts, tensions, and trade-offs architects need to be aware of.

## What to look for:
- Direct conflicts: two NFRs that cannot both be fully satisfied simultaneously
- Tensions: NFRs that pull in opposite directions requiring careful balancing
- Cost implications: combinations that will be expensive or complex to satisfy together
- Hidden dependencies: NFRs that implicitly require other capabilities not mentioned
- Unrealistic combinations: targets that are technically very difficult to achieve together

## Output format:

## NFR Conflict & Tension Analysis

### Direct Conflicts
NFRs that directly contradict each other.

For each conflict:
**NFR-XX vs NFR-YY: [Conflict title]**
- Explanation of why these conflict
- Recommended resolution or trade-off decision

### Tensions & Trade-offs
NFRs that create tension requiring architectural decisions to balance.

For each tension:
**NFR-XX vs NFR-YY: [Tension title]**
- Explanation of the tension
- Architectural patterns that help balance them

### Cost & Complexity Hotspots
Combinations of NFRs that together create significant cost or complexity.

### Hidden Dependencies
NFRs that implicitly require capabilities not explicitly called out.

### Overall Assessment
Brief paragraph summarising NFR health and the most important trade-off decisions the team needs to make.
"""


# â”€â”€ Agent validation prompt â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

REMEDIATION_PROMPT = """You are a Principal Architect specialising in improving weak, risky, or ambiguous NFRs.

Review the provided NFR set and supporting analysis, then recommend concrete remediation actions.

## Rules:
- Focus on the most important improvements first
- Rewrite weak or incomplete NFRs into measurable alternatives where possible
- Consider scoring, conflicts, and gaps when deciding what to remediate
- Do not duplicate the entire NFR set; focus on improvements and rewrites

## Output format:

## NFR Remediation Plan

### Priority Remediation Actions
Short bullet list of the highest-value fixes.

### Suggested Rewrites

| Area | Current Issue | Improved Requirement | Why It Is Better |
|------|---------------|----------------------|------------------|

### Follow-up Decisions
Key decisions or clarifications still needed from stakeholders.
"""


COMPLIANCE_MAPPING_PROMPT = """You are a Senior Compliance Architect specialising in mapping non-functional requirements to common control frameworks.

Map the supplied NFRs and supporting context to common frameworks. This is for planning support and not legal advice.

## Frameworks to consider where relevant:
- ISO 27001
- SOC 2
- GDPR / UK GDPR
- PCI DSS
- NIS2 / operational resilience themes

## Rules:
- Only map frameworks that appear relevant to the described system
- Be clear when coverage is partial or inferred
- Focus on practical control themes rather than legal overstatement

## Output format:

## Compliance Mapping

### Relevant Frameworks
Bullet list of the most relevant frameworks and why they matter here.

### Mapping Matrix

| Framework | NFR Theme / Requirement | Control Area | Coverage View | Notes |
|-----------|-------------------------|--------------|---------------|-------|

### Compliance Gaps
Short list of notable areas where additional controls, evidence, or decisions may be needed.

### Evidence Suggestions
What artefacts or operational evidence should be produced to support compliance.
"""


NFR_VALIDATION_PROMPT = """You are a Senior Solutions Architect specialising in Non-Functional Requirements (NFRs).

Review an existing set of NFRs against a system description and produce a gap analysis.

## Rules:
- Identify missing NFR categories or specific requirements
- Flag NFRs that are too vague to be testable - suggest how to make them measurable
- Flag any NFRs that conflict with each other
- Suggest measurable targets where none are provided
- Never remove or overwrite existing NFRs - only annotate and supplement

## Output format:

## NFR Validation Report

### Coverage Assessment
Overall assessment of how well the existing NFRs cover the system needs.

### Missing NFRs
NFRs that should exist but are absent, grouped by category.

### Vague NFRs (Needs Improvement)
Existing NFRs that are not measurable, with suggested improvements.

### Conflicts
Any NFRs that contradict or create tension with each other.

### Suggested Additions

| Category | Requirement | Rationale | Target |
|----------|-------------|-----------|--------|

### Summary
Overall quality score (1-10) with brief justification.
"""


NFR_FOLLOW_UP_PROMPT = """You are an expert Non-Functional Requirements (NFR) assistant helping a user interrogate an existing NFR pack or validation report.

## Rules:
- Use only the supplied context and conversation history as evidence
- Do not invent NFRs, system details, compliance obligations, or decisions that are not supported by the context
- If the user asks something the context does not answer, say what is missing and what clarification would help
- Reference NFR IDs, report sections, or framework names from the material where helpful
- Be concise, practical, and decision-oriented
- If asked to rewrite or improve an NFR, clearly label the rewrite as a suggestion
- Always return valid markdown
"""


ATTACHMENT_SUMMARY_PROMPT = """You are a Senior Enterprise Architect reviewing a supporting attachment for an NFR assessment.

Summarise only the information that is useful for downstream non-functional analysis.

## Focus areas
- architecture and component boundaries
- integrations, data flows, and dependencies
- scale, performance, resilience, and availability clues
- security, compliance, and operational signals
- uncertainties, assumptions, and missing context

## Rules
- do not invent details that are not visible or stated
- if the attachment is a diagram, describe the visible structure and likely interactions
- if the source content is partial or truncated, say so
- keep the output concise and practical for architects

## Output format

### Attachment Summary
2-4 bullet points covering the most relevant architectural information.

### NFR-Relevant Signals
Bullet points listing the NFR implications or constraints this attachment suggests.

### Uncertainties
Bullet points listing what remains unclear, inferred, or missing.
"""


# â”€â”€ Shared API call helper â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

def _normalise_usage(usage: Any) -> dict[str, int]:
    """Return a stable usage dict from the OpenAI response usage object."""
    if usage is None:
        return {
            "prompt_tokens": 0,
            "completion_tokens": 0,
            "total_tokens": 0,
            "cached_tokens": 0,
            "reasoning_tokens": 0,
        }

    prompt_details = getattr(usage, "prompt_tokens_details", None)
    completion_details = getattr(usage, "completion_tokens_details", None)
    return {
        "prompt_tokens": int(getattr(usage, "prompt_tokens", 0) or 0),
        "completion_tokens": int(getattr(usage, "completion_tokens", 0) or 0),
        "total_tokens": int(getattr(usage, "total_tokens", 0) or 0),
        "cached_tokens": int(getattr(prompt_details, "cached_tokens", 0) or 0),
        "reasoning_tokens": int(getattr(completion_details, "reasoning_tokens", 0) or 0),
    }


def estimate_usage_cost(usage: dict[str, int]) -> float:
    """Estimate request cost from uncached input and output token counts."""
    cached_input_tokens = usage.get("cached_tokens", 0)
    billable_input_tokens = max(
        0,
        usage.get("prompt_tokens", 0) - cached_input_tokens,
    )
    billable_output_tokens = usage.get("completion_tokens", 0)
    input_cost = billable_input_tokens / 1_000_000 * MODEL_PRICING["input_per_million"]
    cached_input_cost = cached_input_tokens / 1_000_000 * MODEL_PRICING["cached_input_per_million"]
    output_cost = billable_output_tokens / 1_000_000 * MODEL_PRICING["output_per_million"]
    return input_cost + cached_input_cost + output_cost


def _call_openai(system_prompt: str, user_content: str, max_tokens: int = 2000) -> AgentRunResult:
    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    response = client.chat.completions.create(
        model=MODEL_NAME,
        max_tokens=max_tokens,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_content}
        ]
    )
    return AgentRunResult(
        content=response.choices[0].message.content,
        usage=_normalise_usage(getattr(response, "usage", None)),
        model=MODEL_NAME,
    )


def _call_openai_parts(system_prompt: str, user_parts: list[dict[str, Any]], max_tokens: int = 2000) -> AgentRunResult:
    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    response = client.chat.completions.create(
        model=MODEL_NAME,
        max_tokens=max_tokens,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_parts},
        ],
    )
    return AgentRunResult(
        content=response.choices[0].message.content,
        usage=_normalise_usage(getattr(response, "usage", None)),
        model=MODEL_NAME,
    )


# â”€â”€ Public agent functions â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

def generate_nfrs(system_description: str, *, retrieved_context: str = "") -> AgentRunResult:
    """Agent 1: Generate NFRs from a system description, optionally augmented with retrieved context."""

    user_content = f"Please generate NFRs for the following system:\n\n{system_description}"
    if retrieved_context.strip():
        user_content = f"{user_content}\n\n{retrieved_context.strip()}"

    return _call_openai(NFR_GENERATION_PROMPT, user_content)


def clarify_gaps(system_description: str) -> AgentRunResult:
    """Agent 0: Identify missing context and working assumptions."""
    return _call_openai(
        GAP_CLARIFICATION_PROMPT,
        f"Please analyse the following system description for missing context:\n\n{system_description}"
    )


def score_nfrs(nfrs: str) -> AgentRunResult:
    """Agent 2: Score and prioritise a set of NFRs."""
    return _call_openai(
        NFR_SCORING_PROMPT,
        f"Please score and prioritise the following NFRs:\n\n{nfrs}"
    )


def generate_test_criteria(nfrs: str, scores: str) -> AgentRunResult:
    """Agent 3: Generate test acceptance criteria from NFRs and scores."""
    return _call_openai(
        TEST_CRITERIA_PROMPT,
        f"""Please generate test acceptance criteria. Focus on critical and high priority items.

## NFRs
{nfrs}

## Priority Scores
{scores}
""",
        max_tokens=2500
    )


def detect_conflicts(nfrs: str) -> AgentRunResult:
    """Agent 4: Detect conflicts and tensions in a set of NFRs."""
    return _call_openai(
        CONFLICT_DETECTION_PROMPT,
        f"Please analyse the following NFRs for conflicts and tensions:\n\n{nfrs}"
    )


def remediate_nfrs(system_description: str, nfrs: str, supporting_analysis: str) -> AgentRunResult:
    """Agent 5: Recommend remediation and stronger NFR wording."""
    return _call_openai(
        REMEDIATION_PROMPT,
        f"""Please create an NFR remediation plan.

## System Description
{system_description}

## NFR Set
{nfrs}

## Supporting Analysis
{supporting_analysis}
""",
        max_tokens=2500,
    )


def map_compliance(system_description: str, nfrs: str, supporting_analysis: str = "") -> AgentRunResult:
    """Agent 6: Map NFR content to common compliance frameworks."""
    return _call_openai(
        COMPLIANCE_MAPPING_PROMPT,
        f"""Please map the following material to relevant compliance frameworks.

## System Description
{system_description}

## NFR Material
{nfrs}

## Supporting Analysis
{supporting_analysis}
""",
        max_tokens=2500,
    )


def validate_nfrs(system_description: str, existing_nfrs: str) -> AgentRunResult:
    """Standalone: Validate existing NFRs against a system description."""
    return _call_openai(
        NFR_VALIDATION_PROMPT,
        f"""## System Description
{system_description}

## Existing NFRs
{existing_nfrs}
"""
    )


def answer_nfr_question(
    context: str,
    question: str,
    history: list[dict[str, str]] | None = None,
) -> AgentRunResult:
    """Answer follow-up questions grounded in the current NFR run context."""
    conversation = ""
    if history:
        recent_messages = history[-6:]
        lines = [
            f"{item['role'].title()}: {item['content']}"
            for item in recent_messages
        ]
        conversation = "\n\n## Recent Conversation\n" + "\n\n".join(lines)

    return _call_openai(
        NFR_FOLLOW_UP_PROMPT,
        f"""## Current NFR Context
{context}
{conversation}

## User Question
{question}
""",
        max_tokens=1400,
    )


def summarize_supporting_attachment(
    filename: str,
    media_type: str,
    *,
    text_content: str | None = None,
    image_bytes: bytes | None = None,
    truncated: bool = False,
    extraction_note: str = "",
) -> AgentRunResult:
    """Summarise a supporting attachment into concise NFR-relevant context."""
    truncated_note = "Yes" if truncated else "No"
    note_text = extraction_note or "Analysed as a supporting attachment."

    if image_bytes is not None:
        encoded = base64.b64encode(image_bytes).decode("ascii")
        return _call_openai_parts(
            ATTACHMENT_SUMMARY_PROMPT,
            [
                {
                    "type": "text",
                    "text": (
                        f"Filename: {filename}\n"
                        f"Media type: {media_type}\n"
                        f"Extraction note: {note_text}\n"
                        f"Content truncated: {truncated_note}\n\n"
                        "Summarise this attachment for downstream NFR analysis."
                    ),
                },
                {
                    "type": "image_url",
                    "image_url": {"url": f"data:{media_type};base64,{encoded}"},
                },
            ],
            max_tokens=900,
        )

    return _call_openai(
        ATTACHMENT_SUMMARY_PROMPT,
        f"""Filename: {filename}
Media type: {media_type}
Extraction note: {note_text}
Content truncated: {truncated_note}

## Attachment Content
{text_content or ""}
""",
        max_tokens=900,
    )
