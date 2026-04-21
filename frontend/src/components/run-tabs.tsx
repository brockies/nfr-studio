import { useMemo, useState } from "react";

import { MarkdownPanel } from "@/components/markdown-panel";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { downloadText } from "@/lib/utils";
import type { Mode, RunPayload } from "@/types";

type Section = {
  key: string;
  label: string;
  content: string;
};

type ComplianceInsights = {
  evidencePlanSection: string;
  proofGapsSection: string;
  evidenceRowCount: number;
  proofGapCount: number;
};

function isProjectScopedSource(source: RunPayload["rag_sources"][number]): boolean {
  return source.project_type.trim().toLowerCase() === "project_attachment";
}

function sourceScopeLabel(source: RunPayload["rag_sources"][number]): string {
  return isProjectScopedSource(source) ? "Project-specific attachment context" : "Shared knowledge base";
}

function formatKnowledgeBaseContent(run: RunPayload): string {
  const sources = run.rag_sources ?? [];
  if (!sources.length) {
    return "No retrieved context sources were found for this run.";
  }

  const lines: string[] = [
    "### Retrieved Context Sources",
    "",
  ];

  for (const source of sources) {
    lines.push(`#### ${source.project_id || sourceScopeLabel(source)} (score: ${source.score.toFixed(3)})`);
    lines.push(`- Scope: ${sourceScopeLabel(source)}`);
    if (source.industry) lines.push(`- Industry: ${source.industry}`);
    if (source.tech_stack) lines.push(`- Tech stack: ${source.tech_stack}`);
    if (source.scale) lines.push(`- Scale: ${source.scale}`);
    if (source.lessons) lines.push(`- Lessons: ${source.lessons}`);
    if (source.source_path) lines.push(`- File: \`${source.source_path}\``);
    lines.push("");
    if (source.snippet) {
      lines.push("```");
      lines.push(source.snippet.trim());
      lines.push("```");
      lines.push("");
    }
  }

  return lines.join("\n").trim();
}

const CLARIFICATION_HEADINGS = new Set([
  "Gap Clarification Analysis",
  "Known Context",
  "Working Assumptions",
  "Clarifying Questions",
  "NFR Impact Areas",
]);

function formatClarificationContent(content: string): string {
  const normalized = content.replace(/\r\n/g, "\n").trim();
  if (!normalized) {
    return content;
  }

  if (/(^|\n)\s*#{1,6}\s/.test(normalized) || /^\s*[-*]\s/m.test(normalized)) {
    return content;
  }

  const lines = normalized
    .split("\n")
    .map((line) => line.trim())
    .filter(Boolean);

  const formatted: string[] = [];
  let currentSection = "";

  for (const line of lines) {
    if (CLARIFICATION_HEADINGS.has(line)) {
      currentSection = line;
      formatted.push(line === "Gap Clarification Analysis" ? `## ${line}` : `### ${line}`);
      continue;
    }

    if (currentSection === "Clarifying Questions") {
      if (/^\d+[.)]\s/.test(line)) {
        formatted.push(line.replace(/^(\d+)[.)]\s*/, "$1. "));
      } else {
        formatted.push(`1. ${line}`);
      }
      continue;
    }

    formatted.push(`- ${line}`);
  }

  return formatted.join("\n\n");
}

function escapeHeadingPattern(value: string): string {
  return value.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
}

function extractMarkdownSection(content: string, heading: string): string {
  const normalized = content.replace(/\r\n/g, "\n");
  const pattern = new RegExp(
    `(^|\\n)###\\s+${escapeHeadingPattern(heading)}\\s*\\n([\\s\\S]*?)(?=\\n###\\s+|\\n##\\s+|$)`,
    "i"
  );
  const match = normalized.match(pattern);
  if (!match) return "";
  return `### ${heading}\n${match[2].trim()}`.trim();
}

function countMarkdownTableRows(section: string): number {
  const lines = section
    .replace(/\r\n/g, "\n")
    .split("\n")
    .map((line) => line.trim())
    .filter(Boolean);

  const tableLines = lines.filter((line) => line.includes("|"));
  if (tableLines.length < 3) return 0;

  return tableLines.filter((line, index) => {
    if (index < 2) return false;
    return /^(\|?.+\|.+)$/.test(line) && !/^\|?[-:\s|]+\|?$/.test(line);
  }).length;
}

function countMarkdownBullets(section: string): number {
  return section
    .replace(/\r\n/g, "\n")
    .split("\n")
    .map((line) => line.trim())
    .filter((line) => /^[-*]\s+/.test(line) || /^\d+\.\s+/.test(line)).length;
}

function getComplianceInsights(content: string): ComplianceInsights {
  const evidencePlanSection = extractMarkdownSection(content, "Prioritised Evidence Plan");
  const proofGapsSection = extractMarkdownSection(content, "Proof Gaps");

  return {
    evidencePlanSection,
    proofGapsSection,
    evidenceRowCount: countMarkdownTableRows(evidencePlanSection),
    proofGapCount: countMarkdownBullets(proofGapsSection),
  };
}

function applicabilityBadgeClass(applicability: string): string {
  const normalized = applicability.trim().toLowerCase();
  if (normalized === "applicable") {
    return "bg-emerald-100 text-emerald-800";
  }
  if (normalized === "potentially applicable") {
    return "bg-amber-100 text-amber-800";
  }
  if (normalized === "not applicable") {
    return "bg-slate-200 text-slate-700";
  }
  return "bg-sky-100 text-sky-800";
}

function applicabilityCardClass(applicability: string): string {
  const normalized = applicability.trim().toLowerCase();
  if (normalized === "applicable") {
    return "border-emerald-200 bg-emerald-50/70";
  }
  if (normalized === "potentially applicable") {
    return "border-amber-200 bg-amber-50/70";
  }
  if (normalized === "not applicable") {
    return "border-slate-200 bg-slate-50/90";
  }
  return "border-sky-200 bg-sky-50/70";
}

function sectionGroups(mode: Mode, run: RunPayload): Section[] {
  if (mode === "generate") {
    const sections: Section[] = [
      {
        key: "clarify",
        label: "Clarification",
        content: formatClarificationContent(run.results.clarify ?? ""),
      },
      { key: "diagram", label: "Diagram", content: run.results.diagram ?? "" },
      { key: "nfr", label: "NFRs", content: run.results.nfr ?? "" },
      { key: "score", label: "Priority Matrix", content: run.results.score ?? "" },
      { key: "test", label: "Test Criteria", content: run.results.test ?? "" },
      { key: "conflict", label: "Conflicts", content: run.results.conflict ?? "" },
      { key: "remediate", label: "Remediation", content: run.results.remediate ?? "" },
      { key: "compliance", label: "Compliance & Evidence", content: run.results.compliance ?? "" }
    ];

    return sections;
  }

  return [
    {
      key: "clarify",
      label: "Clarification",
      content: formatClarificationContent(run.results.clarify ?? ""),
    },
    { key: "validate", label: "Validation", content: run.results.validate ?? "" },
    { key: "remediate", label: "Remediation", content: run.results.remediate ?? "" },
    { key: "compliance", label: "Compliance & Evidence", content: run.results.compliance ?? "" }
  ];
}

export function RunTabs({ run }: { run: RunPayload }) {
  const sections = useMemo(() => sectionGroups(run.mode, run), [run]);
  const [activeTab, setActiveTab] = useState(sections[0]?.key ?? "");
  const activeSection = sections.find((item) => item.key === activeTab) ?? sections[0];
  const ragSummary = useMemo(() => {
    const sources = run.rag_sources ?? [];
    const projectScopedCount = sources.filter(isProjectScopedSource).length;
    const sharedCount = sources.length - projectScopedCount;
    const projectIds = Array.from(new Set(sources.map((item) => item.project_id).filter(Boolean))).sort();

    return {
      totalCount: sources.length,
      projectScopedCount,
      sharedCount,
      projectIds,
    };
  }, [run.rag_sources]);
  const complianceInsights = useMemo(
    () => {
      const fallback = getComplianceInsights(run.results.compliance ?? "");
      const evidencePlan = run.evidence_plan ?? [];
      const proofGaps = run.proof_gaps ?? [];

      return {
        evidencePlanSection:
          evidencePlan.length > 0
            ? [
                "### Prioritised Evidence Plan",
                "",
                "| Priority | NFR / Theme | Evidence Required | Suggested Owner | Suggested Delivery Stage |",
                "|----------|--------------|-------------------|-----------------|--------------------------|",
                ...evidencePlan.map(
                  (item) =>
                    `| ${item.priority || ""} | ${item.nfr_theme || ""} | ${item.evidence_required || ""} | ${item.suggested_owner || ""} | ${item.suggested_delivery_stage || ""} |`
                ),
              ].join("\n")
            : fallback.evidencePlanSection,
        proofGapsSection:
          proofGaps.length > 0
            ? [
                "### Proof Gaps",
                "",
                ...proofGaps.map((item) => `- ${item}`),
              ].join("\n")
            : fallback.proofGapsSection,
        evidenceRowCount: evidencePlan.length || fallback.evidenceRowCount,
        proofGapCount: proofGaps.length || fallback.proofGapCount,
      };
    },
    [run.evidence_plan, run.proof_gaps, run.results.compliance]
  );
  const complianceStats = useMemo(() => {
    const frameworks = run.compliance_frameworks ?? [];
    const mappings = run.compliance_mappings ?? [];
    const applicableCount = frameworks.filter(
      (item) => item.applicability.trim().toLowerCase() === "applicable"
    ).length;
    const potentialCount = frameworks.filter(
      (item) => item.applicability.trim().toLowerCase() === "potentially applicable"
    ).length;

    return {
      frameworkCount: frameworks.length,
      applicableCount,
      potentialCount,
      mappingCount: mappings.length,
    };
  }, [run.compliance_frameworks, run.compliance_mappings]);

  return (
    <Card>
      <CardHeader className="gap-4">
        <div className="flex flex-wrap gap-2">
          {sections.map((section) => (
            <Button
              key={section.key}
              variant={section.key === activeSection.key ? "default" : "outline"}
              size="sm"
              onClick={() => setActiveTab(section.key)}
            >
              {section.label}
            </Button>
          ))}
        </div>
        <CardTitle>{activeSection.label}</CardTitle>
      </CardHeader>
      <CardContent className="space-y-6">
        {activeSection.key === "nfr" || activeSection.key === "validate" ? (
          <div className="rounded-[24px] border border-slate-200 bg-slate-50 px-4 py-3 text-sm text-slate-700">
            {ragSummary.totalCount ? (
              <>
                <div className="flex flex-wrap items-center gap-2">
                  <span className="font-semibold text-slate-900">Retrieved context in use</span>
                  {ragSummary.sharedCount ? (
                    <Badge className="bg-sky-100 text-sky-800">{ragSummary.sharedCount} shared</Badge>
                  ) : null}
                  {ragSummary.projectScopedCount ? (
                    <Badge className="bg-emerald-100 text-emerald-800">
                      {ragSummary.projectScopedCount} project-specific
                    </Badge>
                  ) : null}
                </div>
                {ragSummary.projectIds.length ? (
                  <div className="mt-1">
                    <span className="font-semibold text-slate-900">Projects referenced:</span>{" "}
                    {ragSummary.projectIds.join(", ")}
                  </div>
                ) : null}
                <details className="mt-2">
                  <summary className="cursor-pointer select-none text-sm font-semibold text-slate-900">
                    View retrieved context sources
                  </summary>
                  <div className="mt-3">
                    <MarkdownPanel content={formatKnowledgeBaseContent(run)} />
                  </div>
                </details>
              </>
            ) : (
              <>
                <div className="font-semibold text-slate-900">Knowledge Base</div>
                <div className="mt-1 text-sm text-slate-700">
                  {run.rag_status?.message
                    ? run.rag_status.message
                    : "No retrieved context sources were found for this run."}
                </div>
              </>
            )}
          </div>
        ) : null}
        {activeSection.key === "diagram" ? (
          <div className="rounded-[24px] border border-slate-200 bg-slate-50 px-5 py-4">
            <div className="text-xs font-semibold uppercase tracking-[0.14em] text-slate-500">
              PlantUML Diagram
            </div>
            <div className="mt-1 text-sm text-slate-600">
              Generated system-context diagram source for architecture review and export. Rendering can be added later without changing the underlying artifact.
            </div>
          </div>
        ) : null}
        {activeSection.key === "compliance" ? (
          <div className="space-y-4">
            <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
              <div className="rounded-[24px] border border-slate-200 bg-white px-5 py-4 shadow-sm">
                <div className="text-xs font-semibold uppercase tracking-[0.14em] text-slate-500">
                  Frameworks Assessed
                </div>
                <div className="mt-2 text-3xl font-semibold tracking-tight text-slate-900">
                  {complianceStats.frameworkCount}
                </div>
                <div className="mt-1 text-sm text-slate-600">frameworks reviewed for applicability</div>
              </div>
              <div className="rounded-[24px] border border-emerald-200 bg-emerald-50/80 px-5 py-4 shadow-sm">
                <div className="text-xs font-semibold uppercase tracking-[0.14em] text-emerald-700">
                  Applicable
                </div>
                <div className="mt-2 text-3xl font-semibold tracking-tight text-slate-900">
                  {complianceStats.applicableCount}
                </div>
                <div className="mt-1 text-sm text-slate-700">frameworks that clearly matter here</div>
              </div>
              <div className="rounded-[24px] border border-amber-200 bg-amber-50/80 px-5 py-4 shadow-sm">
                <div className="text-xs font-semibold uppercase tracking-[0.14em] text-amber-700">
                  Potentially Applicable
                </div>
                <div className="mt-2 text-3xl font-semibold tracking-tight text-slate-900">
                  {complianceStats.potentialCount}
                </div>
                <div className="mt-1 text-sm text-slate-700">areas that depend on final scope decisions</div>
              </div>
              <div className="rounded-[24px] border border-sky-200 bg-sky-50/80 px-5 py-4 shadow-sm">
                <div className="text-xs font-semibold uppercase tracking-[0.14em] text-sky-700">
                  Control Mappings
                </div>
                <div className="mt-2 text-3xl font-semibold tracking-tight text-slate-900">
                  {complianceStats.mappingCount}
                </div>
                <div className="mt-1 text-sm text-slate-700">structured framework-to-control links captured</div>
              </div>
            </div>

            {(run.compliance_frameworks ?? []).length > 0 ? (
              <div className="rounded-[24px] border border-slate-200 bg-white px-5 py-4 shadow-sm">
                <div className="text-xs font-semibold uppercase tracking-[0.14em] text-slate-500">
                  Framework Applicability
                </div>
                <div className="mt-1 text-sm text-slate-600">
                  Which control frameworks appear relevant for this system, and why.
                </div>
                <div className="mt-4 space-y-3">
                  {run.compliance_frameworks.map((framework) => (
                    <div
                      key={`${framework.framework}-${framework.applicability}`}
                      className={`rounded-[20px] border px-4 py-4 ${applicabilityCardClass(framework.applicability)}`}
                    >
                      <div className="flex flex-wrap items-center justify-between gap-2">
                        <div className="text-base font-semibold text-slate-900">
                          {framework.framework || "Unnamed framework"}
                        </div>
                        <Badge className={applicabilityBadgeClass(framework.applicability)}>
                          {framework.applicability || "Assessed"}
                        </Badge>
                      </div>
                      {framework.rationale ? (
                        <div className="mt-2 text-sm leading-6 text-slate-700">{framework.rationale}</div>
                      ) : null}
                      {framework.confidence_note ? (
                        <div className="mt-2 text-xs leading-5 text-slate-500">
                          Confidence note: {framework.confidence_note}
                        </div>
                      ) : null}
                    </div>
                  ))}
                </div>
              </div>
            ) : null}

            {(run.compliance_mappings ?? []).length > 0 ? (
              <div className="rounded-[24px] border border-slate-200 bg-white px-5 py-4 shadow-sm">
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <div>
                    <div className="text-xs font-semibold uppercase tracking-[0.14em] text-slate-500">
                      Structured Mapping Matrix
                    </div>
                    <div className="mt-1 text-sm text-slate-600">
                      Framework, control, evidence, and ownership links extracted for quick review.
                    </div>
                  </div>
                  <Badge className="bg-slate-100 text-slate-700">
                    {run.compliance_mappings.length} rows
                  </Badge>
                </div>
                <div className="mt-4 overflow-x-auto">
                  <table className="w-full min-w-[920px] border-collapse overflow-hidden rounded-[20px]">
                    <thead className="bg-slate-100">
                      <tr>
                        <th className="border border-slate-200 px-3 py-2 text-left text-sm font-semibold text-slate-900">
                          Framework
                        </th>
                        <th className="border border-slate-200 px-3 py-2 text-left text-sm font-semibold text-slate-900">
                          Applicability
                        </th>
                        <th className="border border-slate-200 px-3 py-2 text-left text-sm font-semibold text-slate-900">
                          NFR / Theme
                        </th>
                        <th className="border border-slate-200 px-3 py-2 text-left text-sm font-semibold text-slate-900">
                          Control Theme
                        </th>
                        <th className="border border-slate-200 px-3 py-2 text-left text-sm font-semibold text-slate-900">
                          Evidence Required
                        </th>
                        <th className="border border-slate-200 px-3 py-2 text-left text-sm font-semibold text-slate-900">
                          Owner
                        </th>
                        <th className="border border-slate-200 px-3 py-2 text-left text-sm font-semibold text-slate-900">
                          Validation
                        </th>
                      </tr>
                    </thead>
                    <tbody>
                      {run.compliance_mappings.map((item, index) => (
                        <tr key={`${item.framework}-${item.control_theme}-${index}`} className="bg-white">
                          <td className="border border-slate-200 px-3 py-2 align-top text-sm leading-6 text-slate-800">
                            {item.framework || "-"}
                          </td>
                          <td className="border border-slate-200 px-3 py-2 align-top text-sm leading-6 text-slate-800">
                            <Badge className={applicabilityBadgeClass(item.applicability)}>
                              {item.applicability || "Assessed"}
                            </Badge>
                          </td>
                          <td className="border border-slate-200 px-3 py-2 align-top text-sm leading-6 text-slate-800">
                            {item.nfr_theme || "-"}
                          </td>
                          <td className="border border-slate-200 px-3 py-2 align-top text-sm leading-6 text-slate-800">
                            {item.control_theme || "-"}
                          </td>
                          <td className="border border-slate-200 px-3 py-2 align-top text-sm leading-6 text-slate-800">
                            {item.evidence_required || "-"}
                          </td>
                          <td className="border border-slate-200 px-3 py-2 align-top text-sm leading-6 text-slate-800">
                            {item.suggested_owner || "-"}
                          </td>
                          <td className="border border-slate-200 px-3 py-2 align-top text-sm leading-6 text-slate-800">
                            {item.validation_approach || "-"}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            ) : null}

            <div className="grid gap-4 lg:grid-cols-2">
              <div className="rounded-[24px] border border-slate-200 bg-slate-50 px-5 py-4">
                <div className="text-xs font-semibold uppercase tracking-[0.14em] text-slate-500">
                  Evidence Planner
                </div>
                <div className="mt-2 text-3xl font-semibold tracking-tight text-slate-900">
                  {complianceInsights.evidenceRowCount || 0}
                </div>
                <div className="mt-1 text-sm text-slate-600">
                  prioritised evidence actions identified for follow-up
                </div>
                {complianceInsights.evidencePlanSection ? (
                  <details className="mt-4">
                    <summary className="cursor-pointer select-none text-sm font-semibold text-slate-900">
                      View evidence plan
                    </summary>
                    <div className="mt-3 overflow-x-auto">
                      <MarkdownPanel content={complianceInsights.evidencePlanSection} />
                    </div>
                  </details>
                ) : (
                  <div className="mt-4 text-sm text-slate-600">
                    No structured evidence plan was detected in this run yet.
                  </div>
                )}
              </div>

              <div className="rounded-[24px] border border-amber-200 bg-amber-50/80 px-5 py-4">
                <div className="text-xs font-semibold uppercase tracking-[0.14em] text-amber-700">
                  Proof Gaps
                </div>
                <div className="mt-2 text-3xl font-semibold tracking-tight text-slate-900">
                  {complianceInsights.proofGapCount || 0}
                </div>
                <div className="mt-1 text-sm text-slate-700">
                  notable areas where proof, ownership, or validation still looks weak
                </div>
                {complianceInsights.proofGapsSection ? (
                  <details className="mt-4">
                    <summary className="cursor-pointer select-none text-sm font-semibold text-slate-900">
                      View proof gaps
                    </summary>
                    <div className="mt-3 overflow-x-auto">
                      <MarkdownPanel content={complianceInsights.proofGapsSection} />
                    </div>
                  </details>
                ) : (
                  <div className="mt-4 text-sm text-slate-700">
                    No dedicated proof gaps section was detected in this run yet.
                  </div>
                )}
              </div>
            </div>
          </div>
        ) : null}
        <MarkdownPanel content={activeSection.content} />
        <div className="flex flex-wrap gap-3">
          <Button
            variant="outline"
            onClick={() => downloadText(`${activeSection.key}.md`, activeSection.content)}
          >
            Download Section
          </Button>
          <Button variant="secondary" onClick={() => downloadText("nfr-pack.md", run.pack_markdown)}>
            Download Full Pack
          </Button>
        </div>
      </CardContent>
    </Card>
  );
}
