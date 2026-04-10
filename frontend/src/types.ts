export type Mode = "generate" | "validate";
export type RunJobState = "queued" | "running" | "completed" | "failed";

export type UsageStat = {
  label: string;
  model: string;
  prompt_tokens: number;
  completion_tokens: number;
  total_tokens: number;
  cached_tokens: number;
  reasoning_tokens: number;
  estimated_cost: number;
};

export type ChatMessage = {
  role: "user" | "assistant";
  content: string;
};

export type RunPayload = {
  mode: Mode;
  system_description: string;
  existing_nfrs: string;
  project_name: string;
  attachment_context: string;
  result_source: "fresh" | "loaded" | "refined";
  results: Record<string, string>;
  agent_states: Record<string, string>;
  usage_stats: Record<string, UsageStat>;
  counts: {
    nfr_count: number;
    critical_count: number;
    agents_run: number;
  };
  warnings: string[];
  pack_markdown: string;
};

export type SavedRunSummary = {
  file_name: string;
  project_name: string;
  mode: Mode;
  mode_label: string;
  kind_label: string;
  modified: string;
};

export type SavedRunDetail = {
  file_name: string;
  modified: string;
  run: RunPayload;
};

export type SaveRunResponse = {
  file_name: string;
  modified: string;
};

export type FollowUpResponse = {
  answer: string;
  usage: UsageStat;
};

export type RunJobStatus = {
  job_id: string;
  mode: Mode;
  status: RunJobState;
  run: RunPayload | null;
  error: string;
};

export type RedactionPreview = {
  changed: boolean;
  redacted_text: string;
  summary: string;
  items: string[];
  counts: Record<string, number>;
};
