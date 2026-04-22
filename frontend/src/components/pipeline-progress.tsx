import { useEffect, useState } from "react";

import { ArrowRight, CheckCircle2, ChevronDown, ChevronRight, CircleDashed, LoaderCircle } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import type { Mode } from "@/types";

const GENERATE_STEPS = [
  { key: "clarify", title: "Gap Clarification" },
  { key: "diagram", title: "Diagram Generation" },
  { key: "nfr", title: "NFR Generation" },
  { key: "score", title: "Priority Scoring" },
  { key: "test", title: "Test Criteria" },
  { key: "conflict", title: "Conflict Detection" },
  { key: "remediate", title: "Remediation" },
  { key: "compliance", title: "Compliance & Evidence" }
];

const VALIDATE_STEPS = [
  { key: "clarify", title: "Gap Clarification" },
  { key: "validate", title: "Validation" },
  { key: "remediate", title: "Remediation" },
  { key: "compliance", title: "Compliance & Evidence" }
];

function stepStateLabel(state: string): string {
  if (state === "done") return "Completed";
  if (state === "running") return "Running";
  if (state === "failed") return "Failed";
  return "Waiting";
}

function stepBadgeClass(state: string): string {
  if (state === "done") return "bg-emerald-100 text-emerald-700";
  if (state === "running") return "bg-sky-100 text-sky-700";
  if (state === "failed") return "bg-red-100 text-red-700";
  return "bg-slate-100 text-slate-600";
}

function stepCardClass(state: string): string {
  if (state === "done") return "border-emerald-200 bg-emerald-50/70";
  if (state === "running") return "border-sky-200 bg-sky-50/70";
  if (state === "failed") return "border-red-200 bg-red-50/70";
  return "border-slate-200 bg-white/80";
}

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
  const progressPercent = steps.length > 0 ? Math.round((completedCount / steps.length) * 100) : 0;
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
              ? "Eight agents turn a system description into a visualized, prioritized, testable NFR pack."
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
        <div className="mb-5 rounded-[20px] border border-slate-200 bg-slate-50/90 px-4 py-4">
          <div className="flex flex-col gap-3 lg:flex-row lg:items-start lg:justify-between">
            <div>
              <div className="text-xs font-semibold uppercase tracking-[0.14em] text-slate-500">
                Orchestrator View
              </div>
              <div className="mt-1 text-sm leading-6 text-slate-700">
                Read-only workflow map showing how the orchestrator is moving through the current run.
              </div>
            </div>
            <div className="grid grid-cols-3 gap-2 text-sm">
              <div className="rounded-[16px] border border-slate-200 bg-white px-3 py-2">
                <div className="text-[11px] font-semibold uppercase tracking-[0.12em] text-slate-500">Steps</div>
                <div className="mt-1 text-xl font-semibold text-slate-900">{steps.length}</div>
              </div>
              <div className="rounded-[16px] border border-emerald-200 bg-emerald-50/80 px-3 py-2">
                <div className="text-[11px] font-semibold uppercase tracking-[0.12em] text-emerald-700">Done</div>
                <div className="mt-1 text-xl font-semibold text-slate-900">{completedCount}</div>
              </div>
              <div className="rounded-[16px] border border-sky-200 bg-sky-50/80 px-3 py-2">
                <div className="text-[11px] font-semibold uppercase tracking-[0.12em] text-sky-700">Progress</div>
                <div className="mt-1 text-xl font-semibold text-slate-900">{progressPercent}%</div>
              </div>
            </div>
          </div>
          <div className="mt-4 h-2 overflow-hidden rounded-full bg-slate-200">
            <div
              className="h-full rounded-full bg-slate-900 transition-all"
              style={{ width: `${progressPercent}%` }}
            />
          </div>
          <div className="mt-4 overflow-x-auto pb-2">
            <div className="flex min-w-max items-stretch gap-2">
              {steps.map((step, index) => {
                const state = agentStates[step.key] ?? "waiting";
                const Icon =
                  state === "done" ? CheckCircle2 : state === "running" ? LoaderCircle : CircleDashed;

                return (
                  <div key={step.key} className="flex items-center gap-2">
                    <div className={`min-w-[180px] rounded-[18px] border px-4 py-3 ${stepCardClass(state)}`}>
                      <div className="text-[11px] font-semibold uppercase tracking-[0.12em] text-slate-500">
                        Step {index + 1}
                      </div>
                      <div className="mt-1 text-sm font-semibold leading-5 text-slate-900">{step.title}</div>
                      <div className="mt-3 flex items-center justify-between gap-2">
                        <span className={`rounded-full px-2.5 py-0.5 text-xs font-semibold ${stepBadgeClass(state)}`}>
                          {stepStateLabel(state)}
                        </span>
                        <Icon
                          className={`h-4 w-4 shrink-0 ${
                            state === "done"
                              ? "text-emerald-600"
                              : state === "running"
                                ? "animate-spin text-sky-600"
                                : "text-slate-500"
                          }`}
                        />
                      </div>
                    </div>
                    {index < steps.length - 1 ? <ArrowRight className="h-4 w-4 shrink-0 text-slate-400" /> : null}
                  </div>
                );
              })}
            </div>
          </div>
        </div>
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
                    className={`rounded-full px-2.5 py-0.5 text-xs font-semibold ${stepBadgeClass(state)}`}
                  >
                    {stepStateLabel(state)}
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
