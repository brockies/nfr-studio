import { useEffect, useState } from "react";

import { CheckCircle2, ChevronDown, ChevronRight, CircleDashed, LoaderCircle } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import type { Mode } from "@/types";

const GENERATE_STEPS = [
  { key: "clarify", title: "Gap Clarification" },
  { key: "nfr", title: "NFR Generation" },
  { key: "score", title: "Priority Scoring" },
  { key: "test", title: "Test Criteria" },
  { key: "conflict", title: "Conflict Detection" },
  { key: "remediate", title: "Remediation" },
  { key: "compliance", title: "Compliance Mapping" }
];

const VALIDATE_STEPS = [
  { key: "clarify", title: "Gap Clarification" },
  { key: "validate", title: "Validation" },
  { key: "remediate", title: "Remediation" },
  { key: "compliance", title: "Compliance Mapping" }
];

export function PipelineProgress({
  mode,
  agentStates,
  loading
}: {
  mode: Mode;
  agentStates: Record<string, string>;
  loading: boolean;
}) {
  const steps = mode === "generate" ? GENERATE_STEPS : VALIDATE_STEPS;
  const hasRunningState = steps.some((step) => agentStates[step.key] === "running");
  const completedCount = steps.filter((step) => agentStates[step.key] === "done").length;
  const allStepsDone = completedCount === steps.length && steps.length > 0;
  const [collapsed, setCollapsed] = useState(false);

  useEffect(() => {
    if (loading) {
      setCollapsed(false);
      return;
    }

    if (allStepsDone) {
      setCollapsed(true);
    }
  }, [allStepsDone, loading, mode]);

  return (
    <Card className="overflow-hidden">
      <CardHeader className="flex-row items-start justify-between gap-4 pb-4">
        <div>
          <CardTitle className="text-2xl">Agent Status</CardTitle>
          <p className="mt-1 text-xs leading-5 text-muted-foreground sm:text-sm">
            {mode === "generate"
              ? "Seven agents turn a system description into a prioritized, testable NFR pack."
              : "Four agents review the supplied NFR set and tighten the weak spots."}
          </p>
          {loading ? (
            <p className="mt-1.5 text-xs leading-5 text-sky-700 sm:text-sm">
              {hasRunningState
                ? "The highlighted agent is running now."
                : "Preparing the pipeline and waiting for the first agent to start."}
            </p>
          ) : null}
        </div>
        <div className="flex items-center gap-2">
          {allStepsDone ? (
            <button
              className="inline-flex items-center gap-1 rounded-full border border-slate-200 bg-white px-3 py-1 text-sm font-medium text-slate-600 transition-colors hover:border-slate-300 hover:text-slate-900"
              onClick={() => setCollapsed((current) => !current)}
              type="button"
            >
              {collapsed ? (
                <>
                  <ChevronRight className="h-4 w-4" />
                  Show steps
                </>
              ) : (
                <>
                  <ChevronDown className="h-4 w-4" />
                  Hide steps
                </>
              )}
            </button>
          ) : null}
          <Badge className={loading ? "bg-amber-100 text-amber-800" : "bg-emerald-100 text-emerald-800"}>
            {loading ? "Running" : "Ready"}
          </Badge>
        </div>
      </CardHeader>
      <CardContent className="pt-0">
        {collapsed ? (
          <div className="flex items-center justify-between rounded-[16px] border border-emerald-200 bg-emerald-50/70 px-4 py-3 text-sm text-emerald-800">
            <span className="font-medium">
              {mode === "generate" ? "Generate flow completed." : "Validate flow completed."}
            </span>
            <span className="text-emerald-700">
              {completedCount}/{steps.length} steps complete
            </span>
          </div>
        ) : null}
        {!collapsed ? (
        <div className="space-y-2">
          {steps.map((step, index) => {
            const state = agentStates[step.key] ?? "waiting";
            const Icon =
              state === "done" ? CheckCircle2 : state === "running" ? LoaderCircle : CircleDashed;

            return (
              <div
                key={step.key}
                className={`flex flex-col gap-1.5 rounded-[16px] border bg-background/70 px-4 py-2.5 transition-colors sm:flex-row sm:items-center sm:justify-between ${
                  state === "running"
                    ? "border-sky-200 bg-sky-50/70"
                    : state === "done"
                      ? "border-emerald-200"
                      : "border-border"
                }`}
              >
                <div className="min-w-0">
                  <div className="text-xs font-semibold uppercase tracking-[0.14em] text-muted-foreground">
                    Step {index + 1}
                  </div>
                  <div className="mt-0.5 text-base font-semibold leading-6 text-foreground sm:text-lg">
                    {step.title}
                  </div>
                </div>

                <div className="flex items-center gap-2 self-start sm:self-center">
                  <span
                    className={`rounded-full px-2.5 py-0.5 text-xs font-semibold ${
                      state === "done"
                        ? "bg-emerald-100 text-emerald-700"
                        : state === "running"
                          ? "bg-sky-100 text-sky-700"
                          : "bg-slate-100 text-slate-600"
                    }`}
                  >
                    {state === "done"
                      ? "Completed"
                      : state === "running"
                        ? "Running"
                        : "Waiting"}
                  </span>
                  <Icon
                    className={`h-4 w-4 shrink-0 ${
                      state === "done"
                        ? "text-emerald-600"
                        : state === "running"
                          ? "animate-spin text-sky-600"
                          : "text-muted-foreground"
                    }`}
                  />
                </div>
              </div>
            );
          })}
        </div>
        ) : null}
      </CardContent>
    </Card>
  );
}
