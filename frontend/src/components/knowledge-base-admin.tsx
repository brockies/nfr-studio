import { useEffect, useState } from "react";

import { fetchKnowledgeBaseStatus, ingestKnowledgeBase, uploadKnowledgeBaseFile } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";

type Target = "projects" | "compliance";

export function KnowledgeBaseAdmin() {
  const [status, setStatus] = useState<Awaited<ReturnType<typeof fetchKnowledgeBaseStatus>> | null>(null);
  const [loading, setLoading] = useState(false);
  const [target, setTarget] = useState<Target>("projects");
  const [file, setFile] = useState<File | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    let cancelled = false;
    void fetchKnowledgeBaseStatus()
      .then((next) => {
        if (!cancelled) setStatus(next);
      })
      .catch(() => {
        if (!cancelled) setStatus({ indexed: false, reason: "Could not fetch knowledge base status." });
      });
    return () => {
      cancelled = true;
    };
  }, []);

  async function handleIngest() {
    setLoading(true);
    setError("");
    try {
      const next = await ingestKnowledgeBase();
      setStatus(next);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not ingest knowledge base.");
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
      const next = await uploadKnowledgeBaseFile({ file, target });
      setStatus(next);
      setFile(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not upload knowledge base file.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>Knowledge Base Admin</CardTitle>
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

        <div className="grid gap-3 md:grid-cols-[1fr_180px]">
          <Input
            type="file"
            accept=".md"
            onChange={(event) => setFile(event.target.files?.[0] ?? null)}
          />
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
          <Button disabled={loading} variant="outline" onClick={() => void handleIngest()}>
            Reindex Existing Files
          </Button>
        </div>
      </CardContent>
    </Card>
  );
}

