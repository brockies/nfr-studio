import { AlertTriangle, BadgeCheck, CircleHelp, GitCompareArrows, ListChecks } from "lucide-react";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import type { ValidationInsights } from "@/lib/analysis";

export function ValidationInsightsPanel({
  insights,
}: {
  insights: ValidationInsights;
}) {
  const scoreTone =
    insights.qualityScore === null
      ? "bg-slate-100 text-slate-800 border-slate-200"
      : insights.qualityScore >= 8
        ? "bg-emerald-100 text-emerald-800 border-emerald-200"
        : insights.qualityScore >= 5
          ? "bg-amber-100 text-amber-800 border-amber-200"
          : "bg-red-100 text-red-800 border-red-200";

  return (
    <Card>
      <CardHeader>
        <CardTitle>Validation Insights</CardTitle>
        <p className="text-sm text-muted-foreground">
          Quick signals extracted from the validation report to help spot gaps faster.
        </p>
      </CardHeader>
      <CardContent>
        <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-5">
          <InsightCard
            label="Quality Score"
            value={insights.qualityScore === null ? "N/A" : `${insights.qualityScore}/10`}
            icon={BadgeCheck}
            tone={scoreTone}
          />
          <InsightCard
            label="Missing NFRs"
            value={`${insights.missingCount}`}
            icon={CircleHelp}
            tone="bg-sky-100 text-sky-800 border-sky-200"
          />
          <InsightCard
            label="Needs Tightening"
            value={`${insights.vagueCount}`}
            icon={ListChecks}
            tone="bg-amber-100 text-amber-800 border-amber-200"
          />
          <InsightCard
            label="Conflicts"
            value={`${insights.conflictCount}`}
            icon={GitCompareArrows}
            tone="bg-orange-100 text-orange-800 border-orange-200"
          />
          <InsightCard
            label="Suggested Adds"
            value={`${insights.suggestedAdditionsCount}`}
            icon={AlertTriangle}
            tone="bg-violet-100 text-violet-800 border-violet-200"
          />
        </div>
      </CardContent>
    </Card>
  );
}

function InsightCard({
  label,
  value,
  icon: Icon,
  tone,
}: {
  label: string;
  value: string;
  icon: typeof BadgeCheck;
  tone: string;
}) {
  return (
    <div className={`rounded-[24px] border p-4 ${tone}`}>
      <div className="flex items-center justify-between gap-3">
        <div className="text-xs font-semibold uppercase tracking-[0.16em]">{label}</div>
        <Icon className="h-4 w-4" />
      </div>
      <div className="mt-4 text-3xl font-semibold tracking-tight">{value}</div>
    </div>
  );
}
