import { useEffect, useMemo, useState } from "react";

import {
  fetchKnowledgeBaseFiles,
  fetchKnowledgeBaseStatus,
  ingestKnowledgeBase,
  uploadKnowledgeBaseFile,
  type KnowledgeBaseFile
} from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";

type Target = "projects" | "compliance";

function formatBytes(bytes: number) {
  if (!bytes) return "0 B";
  const units = ["B", "KB", "MB", "GB"];
  let size = bytes;
  let idx = 0;
  while (size >= 1024 && idx < units.length - 1) {
    size /= 1024;
    idx += 1;
  }
  return `${size.toFixed(idx === 0 ? 0 : 1)} ${units[idx]}`;
}

function formatTimestamp(seconds: number) {
  if (!seconds) return "";
  const date = new Date(seconds * 1000);
  return date.toLocaleString();
}

export function KnowledgeBasePage({ onClose }: { onClose: () => void }) {
  const [status, setStatus] = useState<Awaited<ReturnType<typeof fetchKnowledgeBaseStatus>> | null>(null);
  const [files, setFiles] = useState<KnowledgeBaseFile[]>([]);
  const [loading, setLoading] = useState(false);
  const [target, setTarget] = useState<Target>("projects");
  const [file, setFile] = useState<File | null>(null);
  const [error, setError] = useState("");
  const [query, setQuery] = useState("");

  async function refreshAll() {
    const [nextStatus, nextFiles] = await Promise.all([fetchKnowledgeBaseStatus(), fetchKnowledgeBaseFiles()]);
    setStatus(nextStatus);
    setFiles(nextFiles);
  }

  useEffect(() => {
    let cancelled = false;
    void refreshAll().catch((err) => {
      if (cancelled) return;
      setError(err instanceof Error ? err.message : "Could not load knowledge base.");
    });
    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const filteredFiles = useMemo(() => {
    const q = query.trim().toLowerCase();
    if (!q) return files;
    return files.filter((item) => {
      const haystack = [
        item.target,
        item.project_id,
        item.industry,
        item.scale,
        item.filename,
        item.relative_path,
        ...(item.tech_stack ?? []),
        ...(item.lessons ?? []),
      ]
        .join(" ")
        .toLowerCase();
      return haystack.includes(q);
    });
  }, [files, query]);

  async function handleIngest() {
    setLoading(true);
    setError("");
    try {
      await ingestKnowledgeBase();
      await refreshAll();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not reindex knowledge base.");
    } finally {
      setLoading(false);
    }
  }

  async function handleUpload() {
    if (!file) {
      setError("Choose a .md file first.");
      return;
    }
    setLoading(true);
    setError("");
    try {
      await uploadKnowledgeBaseFile({ file, target });
      setFile(null);
      await refreshAll();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not upload knowledge base file.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <div className="text-2xl font-semibold tracking-tight">Knowledge Base</div>
          <div className="mt-1 text-sm text-muted-foreground">
            Upload past project NFRs and compliance notes to power retrieval.
          </div>
        </div>
        <Button variant="outline" onClick={onClose}>
          Back to Studio
        </Button>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Index Status</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="rounded-[16px] border border-slate-200 bg-slate-50 px-4 py-3 text-sm text-slate-700">
            <div>
              <span className="font-semibold text-slate-900">Indexed:</span> {status?.indexed ? "Yes" : "No"}
            </div>
            <div>
              <span className="font-semibold text-slate-900">Files:</span> {status?.file_count ?? 0}
            </div>
            <div>
              <span className="font-semibold text-slate-900">Chunks:</span> {status?.chunk_count ?? 0}
            </div>
            {status?.reason ? <div className="mt-1 text-xs text-slate-500">{status.reason}</div> : null}
          </div>

          <div className="flex flex-wrap gap-3">
            <Button disabled={loading} variant="outline" onClick={() => void refreshAll()}>
              Refresh
            </Button>
            <Button disabled={loading} onClick={() => void handleIngest()}>
              {loading ? "Working..." : "Reindex Existing Files"}
            </Button>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Upload New Document</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid gap-3 md:grid-cols-[1fr_180px]">
            <Input type="file" accept=".md" onChange={(event) => setFile(event.target.files?.[0] ?? null)} />
            <select
              className="h-10 rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2"
              value={target}
              onChange={(event) => setTarget(event.target.value as Target)}
            >
              <option value="projects">Projects</option>
              <option value="compliance">Compliance</option>
            </select>
          </div>

          {error ? <div className="text-sm text-red-600">{error}</div> : null}

          <div className="flex flex-wrap gap-3">
            <Button disabled={loading} onClick={() => void handleUpload()}>
              {loading ? "Working..." : "Upload + Reindex"}
            </Button>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader className="gap-3">
          <CardTitle>All Documents</CardTitle>
          <Input
            placeholder="Filter by project id, tech, industry..."
            value={query}
            onChange={(event) => setQuery(event.target.value)}
          />
        </CardHeader>
        <CardContent className="space-y-3">
          {filteredFiles.length === 0 ? (
            <div className="rounded-[24px] border border-dashed border-border p-4 text-sm text-muted-foreground">
              No knowledge base documents found.
            </div>
          ) : null}
          {filteredFiles.map((item) => (
            <div
              key={`${item.target}:${item.relative_path}`}
              className="rounded-[24px] border border-white/70 bg-white/85 p-4 text-sm text-slate-700 shadow-sm"
            >
              <div className="flex flex-wrap items-center justify-between gap-2">
                <div className="text-base font-semibold text-slate-900">{item.project_id || item.filename}</div>
                <div className="text-xs font-semibold uppercase tracking-[0.16em] text-slate-500">{item.target}</div>
              </div>
              <div className="mt-2 grid gap-1 text-sm text-slate-700">
                {item.industry ? <div>Industry: {item.industry}</div> : null}
                {item.scale ? <div>Scale: {item.scale}</div> : null}
                {item.tech_stack?.length ? <div>Tech stack: {item.tech_stack.join(", ")}</div> : null}
                {item.lessons?.length ? <div>Lessons: {item.lessons.join(", ")}</div> : null}
                <div className="text-xs text-slate-500">
                  {item.relative_path} · {formatBytes(item.bytes)} · {formatTimestamp(item.modified)}
                </div>
              </div>
            </div>
          ))}
        </CardContent>
      </Card>
    </div>
  );
}

