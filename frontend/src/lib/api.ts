import type {
  ChatMessage,
  FollowUpResponse,
  RedactionPreview,
  RunJobStatus,
  RunPayload,
  SaveRunResponse,
  SavedRunDetail,
  SavedRunSummary
} from "@/types";

const API_BASE = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";

async function parseResponse<T>(response: Response): Promise<T> {
  if (!response.ok) {
    const payload = await response.json().catch(() => ({}));
    throw new Error(payload.detail ?? "Request failed.");
  }
  return (await response.json()) as T;
}

export async function fetchSavedRuns() {
  const response = await fetch(`${API_BASE}/api/saved-runs`);
  return parseResponse<SavedRunSummary[]>(response);
}

export async function loadSavedRun(filename: string) {
  const response = await fetch(`${API_BASE}/api/saved-runs/${encodeURIComponent(filename)}`);
  return parseResponse<SavedRunDetail>(response);
}

export async function saveRun(filename: string, run: RunPayload) {
  const response = await fetch(`${API_BASE}/api/saved-runs`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json"
    },
    body: JSON.stringify({ filename, run })
  });
  return parseResponse<SaveRunResponse>(response);
}

export async function askFollowUp(run: RunPayload, question: string, history: ChatMessage[]) {
  const response = await fetch(`${API_BASE}/api/follow-up`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json"
    },
    body: JSON.stringify({ run, question, history })
  });
  return parseResponse<FollowUpResponse>(response);
}

export async function previewRedaction(text: string) {
  const response = await fetch(`${API_BASE}/api/redact`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json"
    },
    body: JSON.stringify({ text })
  });
  return parseResponse<RedactionPreview>(response);
}

export async function refineRun(run: RunPayload, additionalContext: string) {
  const response = await fetch(`${API_BASE}/api/refine`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json"
    },
    body: JSON.stringify({ run, additional_context: additionalContext })
  });
  return parseResponse<RunPayload>(response);
}

export async function startGenerateRun(input: {
  systemDescription: string;
  projectName: string;
  files: File[];
}) {
  const formData = new FormData();
  formData.append("system_description", input.systemDescription);
  formData.append("project_name", input.projectName);
  input.files.forEach((file) => formData.append("attachments", file));
  const response = await fetch(`${API_BASE}/api/generate/start`, {
    method: "POST",
    body: formData
  });
  return parseResponse<RunJobStatus>(response);
}

export async function startValidateRun(input: {
  systemDescription: string;
  existingNfrs: string;
  projectName: string;
  files: File[];
}) {
  const formData = new FormData();
  formData.append("system_description", input.systemDescription);
  formData.append("existing_nfrs", input.existingNfrs);
  formData.append("project_name", input.projectName);
  input.files.forEach((file) => formData.append("attachments", file));
  const response = await fetch(`${API_BASE}/api/validate/start`, {
    method: "POST",
    body: formData
  });
  return parseResponse<RunJobStatus>(response);
}

export async function fetchRunJob(jobId: string) {
  const response = await fetch(`${API_BASE}/api/jobs/${encodeURIComponent(jobId)}`);
  return parseResponse<RunJobStatus>(response);
}

export type KnowledgeBaseStatus = {
  indexed?: boolean;
  chunk_count?: number;
  file_count?: number;
  reason?: string;
  provider?: string;
  collection?: string;
  persist_dir?: string;
};

export async function fetchKnowledgeBaseStatus() {
  const response = await fetch(`${API_BASE}/api/kb/status`);
  return parseResponse<KnowledgeBaseStatus>(response);
}

export async function ingestKnowledgeBase() {
  const response = await fetch(`${API_BASE}/api/kb/ingest`, { method: "POST" });
  return parseResponse<KnowledgeBaseStatus>(response);
}

export async function uploadKnowledgeBaseFile(input: { file: File; target: "projects" | "compliance" }) {
  const formData = new FormData();
  formData.append("project_file", input.file);
  formData.append("target", input.target);
  const response = await fetch(`${API_BASE}/api/kb/upload`, {
    method: "POST",
    body: formData
  });
  return parseResponse<KnowledgeBaseStatus>(response);
}
