import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import type { UsageTotals } from "@/lib/analysis";

export function UsageSummary({ totals }: { totals: UsageTotals }) {
  if (totals.totalTokens === 0) {
    return null;
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>Usage Summary</CardTitle>
        <p className="text-sm text-muted-foreground">
          Estimated from per-agent usage returned by the backend.
        </p>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="rounded-[24px] bg-slate-50 p-4 text-sm text-slate-700">
          Usage: {totals.totalTokens.toLocaleString()} total tokens ({totals.promptTokens.toLocaleString()} in,{" "}
          {totals.completionTokens.toLocaleString()} out) and an estimated cost of $
          {totals.estimatedCost.toFixed(4)}.
        </div>
        <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
          <UsageMetric label="Prompt" value={totals.promptTokens.toLocaleString()} />
          <UsageMetric label="Completion" value={totals.completionTokens.toLocaleString()} />
          <UsageMetric label="Cached" value={totals.cachedTokens.toLocaleString()} />
          <UsageMetric label="Reasoning" value={totals.reasoningTokens.toLocaleString()} />
          <UsageMetric label="Total" value={totals.totalTokens.toLocaleString()} />
          <UsageMetric label="Cost (USD)" value={`$${totals.estimatedCost.toFixed(4)}`} />
        </div>
      </CardContent>
    </Card>
  );
}

function UsageMetric({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-[22px] border border-border bg-background/80 p-4">
      <div className="text-xs font-semibold uppercase tracking-[0.18em] text-muted-foreground">
        {label}
      </div>
      <div className="mt-2 text-xl font-semibold tracking-tight text-foreground">{value}</div>
    </div>
  );
}
