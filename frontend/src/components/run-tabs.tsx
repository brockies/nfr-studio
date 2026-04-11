import { useMemo, useState } from "react";

import { MarkdownPanel } from "@/components/markdown-panel";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { downloadText } from "@/lib/utils";
import type { Mode, RunPayload } from "@/types";

type Section = {
  key: string;
  label: string;
  content: string;
};

function formatKnowledgeBaseContent(run: RunPayload): string {
  const sources = run.rag_sources ?? [];
  if (!sources.length) {
    return "No knowledge base sources were retrieved for this run.";
  }

  const projectIds = Array.from(new Set(sources.map((item) => item.project_id).filter(Boolean))).sort();
  const lines: string[] = [
    "## Knowledge Base Retrieval",
    "",
    `Based on insights from: ${projectIds.join(", ")}`,
    "",
    "### Retrieved Chunks",
    "",
  ];

  for (const source of sources) {
    lines.push(`#### ${source.project_id || "unknown_project"} (score: ${source.score.toFixed(3)})`);
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

function sectionGroups(mode: Mode, run: RunPayload): Section[] {
  if (mode === "generate") {
    const sections: Section[] = [
      {
        key: "clarify",
        label: "Clarification",
        content: formatClarificationContent(run.results.clarify ?? ""),
      },
      { key: "nfr", label: "NFRs", content: run.results.nfr ?? "" },
      { key: "score", label: "Priority Matrix", content: run.results.score ?? "" },
      { key: "test", label: "Test Criteria", content: run.results.test ?? "" },
      { key: "conflict", label: "Conflicts", content: run.results.conflict ?? "" },
      { key: "remediate", label: "Remediation", content: run.results.remediate ?? "" },
      { key: "compliance", label: "Compliance", content: run.results.compliance ?? "" }
    ];

    if (run.rag_sources?.length) {
      sections.splice(2, 0, { key: "kb", label: "Knowledge Base", content: formatKnowledgeBaseContent(run) });
    }

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
    { key: "compliance", label: "Compliance", content: run.results.compliance ?? "" }
  ];
}

export function RunTabs({ run }: { run: RunPayload }) {
  const sections = useMemo(() => sectionGroups(run.mode, run), [run]);
  const [activeTab, setActiveTab] = useState(sections[0]?.key ?? "");
  const activeSection = sections.find((item) => item.key === activeTab) ?? sections[0];
  const ragProjectIds = useMemo(() => {
    const sources = run.rag_sources ?? [];
    return Array.from(new Set(sources.map((item) => item.project_id).filter(Boolean))).sort();
  }, [run.rag_sources]);

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
        {activeSection.key === "nfr" && ragProjectIds.length ? (
          <div className="rounded-[24px] border border-slate-200 bg-slate-50 px-4 py-3 text-sm text-slate-700">
            <span className="font-semibold text-slate-900">Based on insights from:</span>{" "}
            {ragProjectIds.join(", ")}
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
