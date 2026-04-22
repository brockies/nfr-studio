import { startTransition, useEffect, useMemo, useState } from "react";

import {
  parseNfrCategoryCounts,
  parsePriorityRows,
  parseValidationInsights,
  summarizeUsage,
} from "@/lib/analysis";
import { CategoryOverview } from "@/components/category-overview";
import { PriorityHeatmap } from "@/components/priority-heatmap";
import { UsageSummary } from "@/components/usage-summary";
import { ValidationInsightsPanel } from "@/components/validation-insights";
import {
  Check,
  FileCog,
  Files,
  LoaderCircle,
  Library,
  Pencil,
  ShieldCheck,
  Sparkles,
  Trash2,
  X
} from "lucide-react";

import { FollowUpChat } from "@/components/follow-up-chat";
import { AttachmentList } from "@/components/attachment-list";
import { KnowledgeBasePage } from "@/components/knowledge-base-page";
import { PipelineProgress } from "@/components/pipeline-progress";
import { RedactionSummary } from "@/components/redaction-summary";
import { RefinementPanel } from "@/components/refinement-panel";
import { RunTabs } from "@/components/run-tabs";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Separator } from "@/components/ui/separator";
import { Textarea } from "@/components/ui/textarea";
import {
  fetchRunJob,
  fetchSavedRuns,
  loadSavedRun,
  deleteSavedRun,
  renameSavedRun,
  refineRun,
  saveRun,
  startGenerateRun,
  startValidateRun
} from "@/lib/api";
import { useRedactionPreview } from "@/hooks/use-redaction-preview";
import { defaultRunFilename, downloadText } from "@/lib/utils";
import type {
  CategoryCount,
  PriorityRow,
  UsageTotals,
  ValidationInsights,
} from "@/lib/analysis";
import type {
  ChatMessage,
  Mode,
  RunJobStatus,
  RunPayload,
  SavedRunSummary
} from "@/types";

const GENERATE_PLACEHOLDER =
  "Example: A high-volume e-commerce order management system processing around 50,000 orders per day. The platform is split across Orders, Payments, Inventory, and Notifications services, deployed on AKS in UK South. It exposes APIs to partner retailers and must handle 5x seasonal peak traffic.";

const VALIDATE_PLACEHOLDER =
  "Paste your current NFRs here in bullet points, markdown tables, or plain text.";

const MODE_SUBTITLE: Record<Mode, string> = {
  generate: "Turn a plain-English system brief into a full NFR pack.",
  validate: "Review an existing NFR set and expose the gaps."
};

type PrivacyMode = "openai" | "local" | "private";

type PrivacyModeDefinition = {
  key: PrivacyMode;
  toggleLabel: string;
  title: string;
  description: string;
};

const PRIVACY_MODES: PrivacyModeDefinition[] = [
  {
    key: "openai",
    toggleLabel: "Cloud",
    title: "OpenAI",
    description: "Fast hosted path for standard cloud inference."
  },
  {
    key: "local",
    toggleLabel: "Local",
    title: "Llama or similar",
    description: "On-device or private-hosted inference for tighter data control."
  },
  {
    key: "private",
    toggleLabel: "Private",
    title: "Bedrock or equivalent",
    description: "Enterprise-style isolated deployment path for higher privacy expectations."
  }
];

type AssessmentProfileDefinition = {
  key: string;
  label: string;
  description: string;
  frameworkPack: string;
  industryProfile: string;
};

const ASSESSMENT_PROFILES: AssessmentProfileDefinition[] = [
  {
    key: "core_saas",
    label: "Core SaaS",
    description: "Balanced baseline for enterprise SaaS products handling security, privacy, and resilience concerns.",
    frameworkPack: "core_saas",
    industryProfile: "saas",
  },
  {
    key: "ai_saas",
    label: "AI SaaS",
    description: "Enterprise SaaS with added emphasis on AI governance, transparency, oversight, and provider risk.",
    frameworkPack: "ai_product",
    industryProfile: "ai_saas",
  },
  {
    key: "ecommerce",
    label: "Ecommerce",
    description: "Customer-facing commerce focus with stronger emphasis on payments, peak scale, resilience, and data handling.",
    frameworkPack: "ecommerce",
    industryProfile: "ecommerce",
  },
  {
    key: "fintech",
    label: "Fintech",
    description: "Regulated financial platform focus with stronger resilience, auditability, change control, and governance expectations.",
    frameworkPack: "fintech",
    industryProfile: "fintech",
  },
  {
    key: "healthtech",
    label: "Healthtech",
    description: "Health-related systems with emphasis on sensitive data handling, traceability, access control, and safety-aware operations.",
    frameworkPack: "health",
    industryProfile: "healthtech",
  },
  {
    key: "public_sector",
    label: "Public Sector",
    description: "Public-service systems with emphasis on accessibility, resilience, supplier assurance, and strong governance evidence.",
    frameworkPack: "public_sector",
    industryProfile: "public_sector",
  }
];

function inferAssessmentProfileKey(frameworkPack: string, industryProfile: string): string {
  const exactMatch = ASSESSMENT_PROFILES.find(
    (profile) =>
      profile.frameworkPack === frameworkPack && profile.industryProfile === industryProfile,
  );

  if (exactMatch) {
    return exactMatch.key;
  }

  const profileMatch = ASSESSMENT_PROFILES.find((profile) => profile.industryProfile === industryProfile);
  if (profileMatch) {
    return profileMatch.key;
  }

  const packMatch = ASSESSMENT_PROFILES.find((profile) => profile.frameworkPack === frameworkPack);
  return packMatch?.key ?? "core_saas";
}

function metricsForRun(run: RunPayload | null) {
  if (!run) {
    return [];
  }
  return [
    { label: "NFR Count", value: `${run.counts.nfr_count}` },
    { label: "Critical Items", value: `${run.counts.critical_count}` },
    { label: "Agents Run", value: `${run.counts.agents_run}` },
    { label: "Mode", value: run.mode === "generate" ? "Generate" : "Validate" }
  ];
}

function groupSavedRuns(items: SavedRunSummary[]): Array<[string, SavedRunSummary[]]> {
  const grouped = new Map<string, SavedRunSummary[]>();

  for (const item of items) {
    const group = item.project_name.trim() || "No Project";
    grouped.set(group, [...(grouped.get(group) ?? []), item]);
  }

  return Array.from(grouped.entries());
}

function savedRunBadges(item: SavedRunSummary): string[] {
  const badges: string[] = [];
  if (item.mode === "validate") {
    badges.push("Validation");
  }
  if (item.kind_label.toLowerCase().includes("refined")) {
    badges.push("Refined");
  }
  return badges;
}

export default function App() {
  const [activePage, setActivePage] = useState<"studio" | "kb">("studio");
  const [mode, setMode] = useState<Mode>("generate");
  const [projectName, setProjectName] = useState("");
  const [systemDescription, setSystemDescription] = useState("");
  const [existingNfrs, setExistingNfrs] = useState("");
  const [assessmentProfile, setAssessmentProfile] = useState("core_saas");
  const [frameworkPack, setFrameworkPack] = useState("core_saas");
  const [industryProfile, setIndustryProfile] = useState("saas");
  const [files, setFiles] = useState<File[]>([]);
  const [run, setRun] = useState<RunPayload | null>(null);
  const [activeJob, setActiveJob] = useState<RunJobStatus | null>(null);
  const [savedRuns, setSavedRuns] = useState<SavedRunSummary[]>([]);
  const [saveName, setSaveName] = useState(defaultRunFilename("generate"));
  const [chatMessages, setChatMessages] = useState<ChatMessage[]>([]);
  const [savedRunQuery, setSavedRunQuery] = useState("");
  const [loading, setLoading] = useState(false);
  const [loadingSavedRuns, setLoadingSavedRuns] = useState(true);
  const [saving, setSaving] = useState(false);
  const [refining, setRefining] = useState(false);
  const [privacyMode, setPrivacyMode] = useState<PrivacyMode>("openai");
  const [renamingFile, setRenamingFile] = useState("");
  const [renameValue, setRenameValue] = useState("");
  const [renaming, setRenaming] = useState(false);
  const [deletingFile, setDeletingFile] = useState("");
  const [error, setError] = useState("");
  const [status, setStatus] = useState("");
  const systemDescriptionPreview = useRedactionPreview(systemDescription);
  const existingNfrsPreview = useRedactionPreview(existingNfrs, mode === "validate");

  useEffect(() => {
    let cancelled = false;

    async function loadSidebar() {
      setLoadingSavedRuns(true);
      try {
        const items = await fetchSavedRuns();
        if (!cancelled) {
          setSavedRuns(items);
        }
      } catch (err) {
        if (!cancelled) {
          setError(err instanceof Error ? err.message : "Could not load saved runs.");
        }
      } finally {
        if (!cancelled) {
          setLoadingSavedRuns(false);
        }
      }
    }

    void loadSidebar();
    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    setSaveName(defaultRunFilename(mode, projectName, run?.result_source === "refined"));
  }, [mode, projectName, run?.result_source]);

  useEffect(() => {
    if (!activeJob || (activeJob.status !== "queued" && activeJob.status !== "running")) {
      return;
    }

    const jobId = activeJob.job_id;
    let cancelled = false;

    async function pollJob() {
      try {
        const nextJob = await fetchRunJob(jobId);
        if (cancelled) {
          return;
        }

        setActiveJob(nextJob);

        if (nextJob.status === "completed" && nextJob.run) {
          startTransition(() => {
            setRun(nextJob.run);
            setChatMessages([]);
          });
          setStatus(nextJob.mode === "generate" ? "NFR pack generated." : "Validation report ready.");
          setError("");
          setLoading(false);
          setActiveJob(null);
          return;
        }

        if (nextJob.status === "failed") {
          setError(nextJob.error || "Run failed.");
          setLoading(false);
          setActiveJob(null);
        }
      } catch (err) {
        if (cancelled) {
          return;
        }
        setError(err instanceof Error ? err.message : "Could not refresh the active run.");
        setLoading(false);
        setActiveJob(null);
      }
    }

    void pollJob();
    const interval = window.setInterval(() => {
      void pollJob();
    }, 1200);

    return () => {
      cancelled = true;
      window.clearInterval(interval);
    };
  }, [activeJob]);

  const displayedRun = activeJob?.run ?? run;
  const progressMode = activeJob?.mode ?? displayedRun?.mode ?? mode;
  const metrics = useMemo(() => metricsForRun(run), [run]);
  const categoryCounts = useMemo<CategoryCount[]>(
    () => (run?.mode === "generate" ? parseNfrCategoryCounts(run.results.nfr ?? "") : []),
    [run],
  );
  const priorityRows = useMemo<PriorityRow[]>(
    () => (run?.mode === "generate" ? parsePriorityRows(run.results.score ?? "") : []),
    [run],
  );
  const usageTotals = useMemo<UsageTotals | null>(
    () => (run ? summarizeUsage(run) : null),
    [run],
  );
  const validationInsights = useMemo<ValidationInsights | null>(
    () => (run?.mode === "validate" ? parseValidationInsights(run.results.validate ?? "") : null),
    [run],
  );
  const selectedPrivacyMode = useMemo(
    () => PRIVACY_MODES.find((modeItem) => modeItem.key === privacyMode) ?? PRIVACY_MODES[0],
    [privacyMode],
  );
  const showRunSidebar = loading || Boolean(activeJob) || Boolean(run);
  const showPipelineProgress = loading || progressMode === mode || Boolean(displayedRun);
  const filteredSavedRuns = useMemo(() => {
    const query = savedRunQuery.trim().toLowerCase();
    return savedRuns.filter((item) => {
      if (!query) {
        return true;
      }

      const haystack = [
        item.file_name,
        item.project_name,
        item.kind_label,
        item.mode_label,
      ]
        .join(" ")
        .toLowerCase();
      return haystack.includes(query);
    });
  }, [savedRuns, savedRunQuery]);
  const groupedSavedRuns = useMemo(() => groupSavedRuns(filteredSavedRuns), [filteredSavedRuns]);

  function handleAssessmentProfileChange(nextProfileKey: string) {
    const nextProfile =
      ASSESSMENT_PROFILES.find((profile) => profile.key === nextProfileKey) ?? ASSESSMENT_PROFILES[0];
    setAssessmentProfile(nextProfile.key);
    setFrameworkPack(nextProfile.frameworkPack);
    setIndustryProfile(nextProfile.industryProfile);
  }

  async function refreshSavedRuns() {
    const items = await fetchSavedRuns();
    setSavedRuns(items);
  }

  async function handleSubmit() {
    setLoading(true);
    setError("");
    setStatus("");
    setRun(null);
    setActiveJob(null);
    setChatMessages([]);

    try {
      const nextJob =
        mode === "generate"
          ? await startGenerateRun({
              systemDescription,
              projectName,
              frameworkPack,
              industryProfile,
              files
            })
          : await startValidateRun({
              systemDescription,
              existingNfrs,
              projectName,
              frameworkPack,
              industryProfile,
              files
            });

      startTransition(() => {
        setActiveJob(nextJob);
      });
    } catch (err) {
      setError(err instanceof Error ? err.message : "Request failed.");
      setLoading(false);
    }
  }

  async function handleLoadSavedRun(fileName: string) {
    setError("");
    setStatus("");
    try {
      const detail = await loadSavedRun(fileName);
      const nextRun = detail.run;
      setLoading(false);
      startTransition(() => {
        setActiveJob(null);
        setRun(nextRun);
        setMode(nextRun.mode);
        setProjectName(nextRun.project_name);
        setAssessmentProfile(
          inferAssessmentProfileKey(nextRun.framework_pack || "core_saas", nextRun.industry_profile || "saas"),
        );
        setFrameworkPack(nextRun.framework_pack || "core_saas");
        setIndustryProfile(nextRun.industry_profile || "saas");
        setSystemDescription(nextRun.system_description);
        setExistingNfrs(nextRun.existing_nfrs);
        setFiles([]);
        setChatMessages([]);
      });
      setStatus(`Loaded ${detail.file_name}.`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not load the saved run.");
    }
  }

  async function handleSaveRun() {
    if (!run) {
      return;
    }

    setSaving(true);
    setError("");
    setStatus("");

    try {
      const response = await saveRun(saveName, {
        ...run,
        project_name: projectName
      });
      setStatus(`Saved as ${response.file_name}.`);
      await refreshSavedRuns();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not save the run.");
    } finally {
      setSaving(false);
    }
  }

  async function handleRenameSavedRun(currentFilename: string) {
    const trimmedValue = renameValue.trim();
    if (!trimmedValue) {
      setError("Please enter a new run name.");
      return;
    }

    setRenaming(true);
    setError("");
    setStatus("");

    try {
      const response = await renameSavedRun(currentFilename, trimmedValue);
      await refreshSavedRuns();
      setStatus(`Renamed to ${response.file_name}.`);
      setRenamingFile("");
      setRenameValue("");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not rename the saved run.");
    } finally {
      setRenaming(false);
    }
  }

  async function handleDeleteSavedRun(fileName: string) {
    const confirmed = window.confirm(`Delete saved run "${fileName}"? This cannot be undone.`);
    if (!confirmed) {
      return;
    }

    setDeletingFile(fileName);
    setError("");
    setStatus("");

    try {
      await deleteSavedRun(fileName);
      if (run && saveName === fileName) {
        setSaveName(defaultRunFilename(mode, projectName));
      }
      await refreshSavedRuns();
      setStatus(`Deleted ${fileName}.`);
      if (renamingFile === fileName) {
        setRenamingFile("");
        setRenameValue("");
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not delete the saved run.");
    } finally {
      setDeletingFile("");
    }
  }

  function resetCurrentRun() {
    setActiveJob(null);
    setLoading(false);
    setRun(null);
    setChatMessages([]);
    setStatus("");
    setError("");
    setFiles([]);
  }

  function handleAttachmentSelection(nextFiles: FileList | null) {
    if (!nextFiles) {
      return;
    }
    setFiles((current) => [...current, ...Array.from(nextFiles)]);
  }

  function removeAttachment(index: number) {
    setFiles((current) => current.filter((_, currentIndex) => currentIndex !== index));
  }

  function clearAttachments() {
    setFiles([]);
  }

  async function handleRefine(additionalContext: string) {
    if (!run) {
      return;
    }

    setRefining(true);
    setError("");
    setStatus("");

    try {
      const nextRun = await refineRun(
        {
          ...run,
          project_name: projectName
        },
        additionalContext,
      );
      startTransition(() => {
        setRun(nextRun);
        setSystemDescription(nextRun.system_description);
        setExistingNfrs(nextRun.existing_nfrs);
        setChatMessages([]);
      });
      setStatus("Run refined with the additional context.");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not refine the run.");
    } finally {
      setRefining(false);
    }
  }

  return (
	    <div className="mx-auto flex min-h-screen max-w-[1760px] gap-5 overflow-x-hidden px-4 py-2 lg:px-6">
		      <aside className="hidden w-[320px] shrink-0 lg:block xl:w-[340px]">
	        <div className="glass-panel sticky top-1 h-[calc(100vh-0.5rem)] overflow-y-auto rounded-[32px] border border-white/70 p-4 shadow-panel">
	          <div className="mb-4 shrink-0">
	            <div className="flex items-center gap-3">
	              <div className="inline-flex h-12 w-12 items-center justify-center rounded-2xl bg-sky-100 text-sky-700">
	                <Sparkles className="h-6 w-6" />
	              </div>
	              <h1 className="text-2xl font-semibold tracking-tight">Architecture Assurance Studio</h1>
	            </div>
	            <p className="mt-2 max-w-[18rem] text-sm leading-6 text-muted-foreground">
	              Define requirements, map controls, and plan the evidence you will need later.
	            </p>
	          </div>

	          <div className="shrink-0 space-y-2.5">
	            <Button
	              className="w-full justify-start"
	              variant={activePage === "studio" && mode === "generate" ? "default" : "outline"}
	              onClick={() => {
	                setActivePage("studio");
	                setMode("generate");
	              }}
	            >
	              <Files className="mr-2 h-4 w-4" />
	              Generate NFR Pack
	            </Button>
	            <Button
	              className="w-full justify-start"
	              variant={activePage === "studio" && mode === "validate" ? "default" : "outline"}
	              onClick={() => {
	                setActivePage("studio");
	                setMode("validate");
	              }}
	            >
	              <ShieldCheck className="mr-2 h-4 w-4" />
	              Validate Existing NFRs
	            </Button>
	            <Button
	              className="w-full justify-start"
	              variant={activePage === "kb" ? "default" : "outline"}
	              onClick={() => setActivePage("kb")}
	            >
	              <Library className="mr-2 h-4 w-4" />
	              Project Collections
	            </Button>
	          </div>

          <Separator className="my-4" />

          <div className="shrink-0 space-y-3">
            <Input
              placeholder="Search runs..."
              value={savedRunQuery}
              onChange={(event) => setSavedRunQuery(event.target.value)}
            />
          </div>

          <Separator className="my-4" />

          <div>
            <div className="mb-3 flex items-center justify-between">
              <div className="text-sm font-semibold">Saved Runs</div>
              {loadingSavedRuns ? <LoaderCircle className="h-4 w-4 animate-spin text-muted-foreground" /> : null}
            </div>
            <p className="mb-3 text-sm leading-6 text-muted-foreground">
              Open a previous run without re-running the pipeline.
            </p>
            <div className="space-y-2">
              {savedRuns.length === 0 && !loadingSavedRuns ? (
                <div className="rounded-[24px] border border-dashed border-border p-4 text-sm text-muted-foreground">
                  No saved runs yet.
                </div>
              ) : null}
              {savedRuns.length > 0 && filteredSavedRuns.length === 0 ? (
                <div className="rounded-[24px] border border-dashed border-border p-4 text-sm text-muted-foreground">
                  No saved runs match the current filters.
                </div>
              ) : null}
              {groupedSavedRuns.map(([groupName, items]) => (
                <div key={groupName} className="space-y-2">
                  {groupName !== "No Project" ? (
                    <div className="px-1 text-sm font-semibold text-slate-600">
                      {groupName}
                    </div>
                  ) : null}
                  {items.map((item) => {
                    const badges = savedRunBadges(item);

                    return (
                      <div
                        key={item.file_name}
                        className="rounded-[18px] border border-slate-200/80 bg-white/90 px-3.5 py-2.5 shadow-sm transition-all hover:-translate-y-0.5 hover:border-sky-200 hover:shadow-md"
                      >
                        <div className="mb-1.5 flex items-start justify-between gap-3">
                          <div className="flex flex-wrap gap-2">
                            {badges.map((badge) => (
                              <span
                                key={`${item.file_name}-${badge}`}
                                className="rounded-full bg-slate-100 px-2.5 py-1 text-[10px] font-semibold uppercase tracking-[0.08em] text-slate-600"
                              >
                                {badge}
                              </span>
                            ))}
                          </div>
                        </div>
                        {renamingFile === item.file_name ? (
                          <div className="space-y-2">
                            <Input
                              autoFocus
                              value={renameValue}
                              onChange={(event) => setRenameValue(event.target.value)}
                              onKeyDown={(event) => {
                                if (event.key === "Enter") {
                                  void handleRenameSavedRun(item.file_name);
                                }
                                if (event.key === "Escape") {
                                  setRenamingFile("");
                                  setRenameValue("");
                                }
                              }}
                            />
                            <div className="flex gap-2">
                              <Button
                                size="sm"
                                disabled={renaming}
                                onClick={() => void handleRenameSavedRun(item.file_name)}
                              >
                                <Check className="mr-1 h-3.5 w-3.5" />
                                Save
                              </Button>
                              <Button
                                size="sm"
                                variant="outline"
                                onClick={() => {
                                  setRenamingFile("");
                                  setRenameValue("");
                                }}
                              >
                                <X className="mr-1 h-3.5 w-3.5" />
                                Cancel
                              </Button>
                            </div>
                          </div>
                        ) : (
                          <button
                            className="w-full min-w-0 text-left"
                            onClick={() => void handleLoadSavedRun(item.file_name)}
                            type="button"
                          >
                            <div className="flex items-center justify-between gap-3">
                              <div className="overflow-hidden text-ellipsis whitespace-nowrap text-sm font-semibold leading-5 text-foreground">
                                {item.file_name}
                              </div>
                              <div className="flex items-center gap-1">
                                <span
                                  className="rounded-full p-1.5 text-slate-400 transition hover:bg-slate-100 hover:text-slate-700"
                                  onClick={(event) => {
                                    event.preventDefault();
                                    event.stopPropagation();
                                    setRenamingFile(item.file_name);
                                    setRenameValue(item.file_name);
                                  }}
                                  role="button"
                                  tabIndex={0}
                                  onKeyDown={(event) => {
                                    if (event.key === "Enter" || event.key === " ") {
                                      event.preventDefault();
                                      event.stopPropagation();
                                      setRenamingFile(item.file_name);
                                      setRenameValue(item.file_name);
                                    }
                                  }}
                                >
                                  <Pencil className="h-3.5 w-3.5" />
                                </span>
                                <span
                                  className="rounded-full p-1.5 text-slate-400 transition hover:bg-red-50 hover:text-red-600"
                                  onClick={(event) => {
                                    event.preventDefault();
                                    event.stopPropagation();
                                    if (!deletingFile) {
                                      void handleDeleteSavedRun(item.file_name);
                                    }
                                  }}
                                  role="button"
                                  tabIndex={0}
                                  onKeyDown={(event) => {
                                    if (event.key === "Enter" || event.key === " ") {
                                      event.preventDefault();
                                      event.stopPropagation();
                                      if (!deletingFile) {
                                        void handleDeleteSavedRun(item.file_name);
                                      }
                                    }
                                  }}
                                >
                                  {deletingFile === item.file_name ? (
                                    <LoaderCircle className="h-3.5 w-3.5 animate-spin" />
                                  ) : (
                                    <Trash2 className="h-3.5 w-3.5" />
                                  )}
                                </span>
                              </div>
                            </div>
                            <div className="mt-0.5 text-xs text-slate-500">{item.modified}</div>
                          </button>
                        )}
                      </div>
                    );
                  })}
                </div>
              ))}
            </div>
          </div>
        </div>
      </aside>

	      <main className="min-w-0 flex-1 space-y-4">
	        {error ? <div className="rounded-[20px] border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">{error}</div> : null}
	        {status ? <div className="rounded-[20px] border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm text-emerald-700">{status}</div> : null}

	        {activePage === "kb" ? (
	          <KnowledgeBasePage onClose={() => setActivePage("studio")} />
	        ) : null}

	        {activePage === "studio" ? (
	        <div className={`grid min-w-0 gap-5 ${showRunSidebar ? "2xl:grid-cols-[1.05fr_0.95fr]" : ""}`}>
	          <Card className="glass-panel min-w-0">
            <CardHeader className="pb-3">
              <div className="flex flex-col gap-3 lg:flex-row lg:items-start lg:justify-between">
                <div className="space-y-2">
                  <CardTitle>{mode === "generate" ? "Describe Your System" : "Provide Review Inputs"}</CardTitle>
                  <CardDescription>
                    Sensitive values should still be masked server-side before they are sent to the model.
                  </CardDescription>
                </div>
                <div className="flex flex-wrap items-start gap-2 lg:justify-end">
                  <Badge className="w-fit bg-slate-900 text-white">
                    {mode === "generate" ? "Generate Mode" : "Validate Mode"}
                  </Badge>
                  {run ? (
                    <>
                    <Button
                      className="whitespace-nowrap"
                      variant="outline"
                      onClick={() => downloadText("nfr-pack.md", run.pack_markdown)}
                    >
                      <FileCog className="mr-2 h-4 w-4" />
                      Download Pack
                    </Button>
                    <Button className="whitespace-nowrap" variant="secondary" onClick={resetCurrentRun}>
                      Start New Run
                    </Button>
                    </>
                  ) : null}
                </div>
              </div>
            </CardHeader>
            <CardContent className="space-y-4 pt-0">
              <div className="rounded-[24px] border border-slate-200 bg-slate-50 px-4 py-4">
                <div className="space-y-3">
                  <div className="flex flex-col gap-3 xl:flex-row xl:items-start xl:justify-between">
                    <div className="min-w-0 xl:max-w-[60%]">
                      <div className="text-xs font-semibold uppercase tracking-[0.14em] text-slate-500">
                        Privacy Mode
                      </div>
                      <div className="mt-1 text-sm text-slate-700">
                        Choose the model deployment path that best fits the privacy expectations for this run.
                      </div>
                    </div>
                    <div className="inline-flex w-fit self-start rounded-full border border-slate-200 bg-white p-1 shadow-sm xl:self-auto">
                      {PRIVACY_MODES.map((modeItem) => (
                        <button
                          key={modeItem.key}
                          type="button"
                          className={`rounded-full px-4 py-2 text-sm font-semibold transition ${
                            privacyMode === modeItem.key
                              ? modeItem.key === "local"
                                ? "bg-emerald-600 text-white"
                                : modeItem.key === "private"
                                  ? "bg-sky-700 text-white"
                                  : "bg-slate-900 text-white"
                              : "text-slate-600 hover:bg-slate-100"
                          }`}
                          onClick={() => setPrivacyMode(modeItem.key)}
                        >
                          {modeItem.toggleLabel}
                        </button>
                      ))}
                    </div>
                  </div>
                  <div className="text-xs leading-5 text-slate-500">
                    <span className="font-semibold text-slate-700">{selectedPrivacyMode.title}:</span>{" "}
                    {selectedPrivacyMode.description} UI-only for now. This does not change backend routing yet.
                  </div>
                </div>
              </div>

              <div className="grid gap-4 xl:grid-cols-[1.25fr_1fr]">
                <div className="space-y-2">
                  <label className="text-sm font-semibold">Project</label>
                  <Input
                    placeholder="Payments Modernisation"
                    value={projectName}
                    onChange={(event) => setProjectName(event.target.value)}
                  />
                  <div className="text-xs leading-5 text-slate-500">
                    Optional label used for saved runs and project-scoped retrieval context.
                  </div>
                </div>

                <div className="space-y-2">
                  <label className="text-sm font-semibold">Assessment profile</label>
                  <select
                    className="flex h-11 w-full rounded-[18px] border border-input bg-background px-3 py-2 text-sm ring-offset-background transition focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-slate-300"
                    value={assessmentProfile}
                    onChange={(event) => handleAssessmentProfileChange(event.target.value)}
                  >
                    {ASSESSMENT_PROFILES.map((profile) => (
                      <option key={profile.key} value={profile.key}>
                        {profile.label}
                      </option>
                    ))}
                  </select>
                  <div className="text-xs leading-5 text-slate-500">
                    Choose the lens that should steer likely frameworks, NFR themes, and evidence expectations for this run.
                  </div>
                  <div className="text-xs leading-5 text-slate-500">
                    {ASSESSMENT_PROFILES.find((profile) => profile.key === assessmentProfile)?.description ??
                      "Choose the lens that should bias likely frameworks, NFR themes, and evidence expectations."}
                  </div>
                </div>
              </div>

              <div className="space-y-2">
                <label className="text-sm font-semibold">System description</label>
                <Textarea
                  className="min-h-[220px]"
                  placeholder={GENERATE_PLACEHOLDER}
                  value={systemDescription}
                  onChange={(event) => setSystemDescription(event.target.value)}
                />
                <RedactionSummary
                  label="System description"
                  preview={systemDescription.trim() ? systemDescriptionPreview : null}
                />
              </div>

              {mode === "validate" ? (
                <div className="space-y-2">
                  <label className="text-sm font-semibold">Existing NFRs</label>
                  <Textarea
                    className="min-h-[200px]"
                    placeholder={VALIDATE_PLACEHOLDER}
                    value={existingNfrs}
                    onChange={(event) => setExistingNfrs(event.target.value)}
                  />
                  <RedactionSummary
                    label="Existing NFRs"
                    preview={existingNfrs.trim() ? existingNfrsPreview : null}
                  />
                </div>
              ) : null}

              <div className="space-y-2">
                <label className="text-sm font-semibold">Supporting attachments</label>
                <Input
                  multiple
                  type="file"
                  onChange={(event) => {
                    handleAttachmentSelection(event.target.files);
                    event.currentTarget.value = "";
                  }}
                />
                <AttachmentList
                  files={files}
                  onRemove={removeAttachment}
                  onClear={clearAttachments}
                />
              </div>

              <div className="flex flex-wrap gap-3">
                <Button
                  disabled={
                    loading ||
                    !systemDescription.trim() ||
                    (mode === "validate" && !existingNfrs.trim())
                  }
                  onClick={() => void handleSubmit()}
                  size="lg"
                >
                  {loading ? (
                    <>
                      <LoaderCircle className="mr-2 h-4 w-4 animate-spin" />
                      Running pipeline...
                    </>
                  ) : mode === "generate" ? (
                    "Run Generate Pipeline"
                  ) : (
                    "Run Validation"
                  )}
                </Button>
                <Button
                  variant="outline"
                  onClick={() => {
                    setSystemDescription("");
                    setExistingNfrs("");
                    handleAssessmentProfileChange("core_saas");
                    setFiles([]);
                    setActiveJob(null);
                    setLoading(false);
                    setRun(null);
                    setChatMessages([]);
                  }}
                >
                  Clear inputs
                </Button>
              </div>

            </CardContent>
          </Card>

          {showRunSidebar ? (
            <div className="min-w-0 space-y-6">
              {showPipelineProgress ? (
                <PipelineProgress
                  mode={progressMode}
                  agentStates={displayedRun?.agent_states ?? {}}
                  loading={loading}
                />
              ) : null}

              {metrics.length > 0 ? (
                <div className="flex gap-3 overflow-x-auto pb-1">
                  {metrics.map((metric) => (
                    <Card
                      key={metric.label}
                      className="min-w-[150px] flex-1 border-white/70 bg-white/85 shadow-sm"
                    >
                      <CardContent className="px-4 py-3">
                        <div className="text-[11px] font-semibold uppercase tracking-[0.18em] text-muted-foreground">
                          {metric.label}
                        </div>
                        <div className="mt-1.5 text-2xl font-semibold leading-none tracking-tight">
                          {metric.value}
                        </div>
                      </CardContent>
                    </Card>
                  ))}
                </div>
              ) : null}

              {run?.warnings.length ? (
                <Card>
                  <CardHeader>
                    <CardTitle>Attachment Warnings</CardTitle>
                  </CardHeader>
                  <CardContent className="space-y-2 text-sm text-muted-foreground">
                    {run.warnings.map((warning) => (
                      <div key={warning}>{warning}</div>
                    ))}
                  </CardContent>
                </Card>
              ) : null}

              {run?.attachment_context ? (
                <Card>
                  <CardHeader>
                    <CardTitle>Supporting Attachment Context</CardTitle>
                  </CardHeader>
                  <CardContent>
                    <pre className="overflow-x-auto whitespace-pre-wrap rounded-[24px] bg-slate-50 p-4 text-sm text-slate-700">
                      {run.attachment_context}
                    </pre>
                  </CardContent>
                </Card>
              ) : null}

              {usageTotals ? <UsageSummary totals={usageTotals} /> : null}
            </div>
	          ) : null}
	        </div>
	        ) : null}

	        {run ? (
	          <>
	            {run.mode === "generate" ? (
	              <div className="grid gap-6 2xl:grid-cols-[0.95fr_1.05fr]">
                <CategoryOverview items={categoryCounts} />
                <PriorityHeatmap rows={priorityRows} />
              </div>
            ) : null}
            {run.mode === "validate" && validationInsights ? (
              <ValidationInsightsPanel insights={validationInsights} />
            ) : null}

            <RunTabs run={run} />

	            <div className="grid gap-6 2xl:grid-cols-[0.9fr_1.1fr]">
              <div className="space-y-6">
                <Card>
                  <CardHeader>
                    <CardTitle>Save This Run</CardTitle>
                    <CardDescription>
                      Persist the current pack to the existing local `saved_runs/` directory.
                      It will be grouped in the sidebar using the project name from above.
                    </CardDescription>
                  </CardHeader>
                  <CardContent className="space-y-4">
                    <div className="rounded-[16px] border border-slate-200 bg-slate-50 px-4 py-3 text-sm text-slate-600">
                      <span className="font-semibold text-slate-900">Project group:</span>{" "}
                      {projectName.trim() ? projectName.trim() : "No Project"}
                    </div>
                    <Input value={saveName} onChange={(event) => setSaveName(event.target.value)} />
                    <div className="flex gap-3">
                      <Button disabled={saving} onClick={() => void handleSaveRun()}>
                        {saving ? "Saving..." : "Save Run"}
                      </Button>
                      <Button
                        variant="outline"
                        onClick={() => downloadText(saveName || "nfr-pack.md", run.pack_markdown)}
                      >
                        Download Markdown
                      </Button>
                    </div>
                  </CardContent>
                </Card>

                <RefinementPanel
                  run={{ ...run, project_name: projectName }}
                  loading={refining}
                  onRefine={handleRefine}
                />
              </div>

              <FollowUpChat
                run={{ ...run, project_name: projectName }}
                messages={chatMessages}
                onMessagesChange={setChatMessages}
              />
            </div>
          </>
        ) : null}
      </main>
    </div>
  );
}
