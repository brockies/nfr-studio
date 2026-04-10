import type { RunPayload } from "@/types";

export type CategoryCount = {
  label: string;
  count: number;
};

export type PriorityRow = {
  id: string;
  label: string;
  risk: number;
  complexity: number;
  priority: "CRITICAL" | "HIGH" | "MEDIUM" | "LOW" | string;
};

export type UsageTotals = {
  promptTokens: number;
  completionTokens: number;
  totalTokens: number;
  cachedTokens: number;
  reasoningTokens: number;
  estimatedCost: number;
};

export type ValidationInsights = {
  qualityScore: number | null;
  missingCount: number;
  vagueCount: number;
  conflictCount: number;
  suggestedAdditionsCount: number;
};

export function parseNfrCategoryCounts(nfrText: string): CategoryCount[] {
  const counts = new Map<string, number>();
  let currentCategory = "";

  for (const rawLine of nfrText.split("\n")) {
    const line = rawLine.trim();
    if (line.startsWith("#### ")) {
      currentCategory = line.slice(5).trim();
      if (!counts.has(currentCategory)) {
        counts.set(currentCategory, 0);
      }
      continue;
    }

    if (currentCategory && /^\|\s*NFR-\d+/i.test(line)) {
      counts.set(currentCategory, (counts.get(currentCategory) ?? 0) + 1);
    }
  }

  return Array.from(counts.entries())
    .filter(([, count]) => count > 0)
    .map(([label, count]) => ({ label, count }));
}

export function parsePriorityRows(scoreText: string): PriorityRow[] {
  const rows: PriorityRow[] = [];

  for (const rawLine of scoreText.split("\n")) {
    const line = rawLine.trim();
    if (!line.startsWith("| NFR-")) {
      continue;
    }

    const parts = line
      .replace(/^\|/, "")
      .replace(/\|$/, "")
      .split("|")
      .map((part) => part.trim());

    if (parts.length < 5) {
      continue;
    }

    const risk = Number(parts[2]);
    const complexity = Number(parts[3]);
    if (Number.isNaN(risk) || Number.isNaN(complexity)) {
      continue;
    }

    rows.push({
      id: parts[0],
      label: parts[1],
      risk,
      complexity,
      priority: parts[4].toUpperCase(),
    });
  }

  return rows;
}

export function summarizeUsage(run: RunPayload): UsageTotals {
  const totals: UsageTotals = {
    promptTokens: 0,
    completionTokens: 0,
    totalTokens: 0,
    cachedTokens: 0,
    reasoningTokens: 0,
    estimatedCost: 0,
  };

  for (const item of Object.values(run.usage_stats)) {
    totals.promptTokens += item.prompt_tokens;
    totals.completionTokens += item.completion_tokens;
    totals.totalTokens += item.total_tokens;
    totals.cachedTokens += item.cached_tokens;
    totals.reasoningTokens += item.reasoning_tokens;
    totals.estimatedCost += item.estimated_cost;
  }

  return totals;
}

function extractMarkdownSection(content: string, title: string): string {
  const escapedTitle = title.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
  const pattern = new RegExp(`^### ${escapedTitle}\\n([\\s\\S]*?)(?=^### |\\Z)`, "m");
  const match = content.match(pattern);
  return match?.[1]?.trim() ?? "";
}

function countMarkdownTableRows(section: string): number {
  return section
    .split("\n")
    .map((line) => line.trim())
    .filter((line) => line.startsWith("|"))
    .filter((line) => !/^\|\s*-+/.test(line))
    .filter((line) => !/^\|\s*(category|framework|id|nfr)\s*\|/i.test(line))
    .length;
}

function countMarkdownListItems(section: string): number {
  return section
    .split("\n")
    .map((line) => line.trim())
    .filter((line) => /^[-*]\s+/.test(line) || /^\d+\.\s+/.test(line) || /^\*\*.+\*\*$/.test(line))
    .length;
}

function countSectionItems(section: string): number {
  return countMarkdownListItems(section) + countMarkdownTableRows(section);
}

export function parseValidationInsights(validationText: string): ValidationInsights {
  const missing = extractMarkdownSection(validationText, "Missing NFRs");
  const vague = extractMarkdownSection(validationText, "Vague NFRs (Needs Improvement)");
  const conflicts = extractMarkdownSection(validationText, "Conflicts");
  const additions = extractMarkdownSection(validationText, "Suggested Additions");

  const qualityScoreMatch = validationText.match(/quality score[^0-9]*([0-9]+(?:\.[0-9]+)?)/i);

  return {
    qualityScore: qualityScoreMatch ? Number(qualityScoreMatch[1]) : null,
    missingCount: countSectionItems(missing),
    vagueCount: countSectionItems(vague),
    conflictCount: countSectionItems(conflicts),
    suggestedAdditionsCount: countSectionItems(additions),
  };
}
