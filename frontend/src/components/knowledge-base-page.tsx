import { useEffect, useState } from "react";

import {
  fetchChromaCollectionPreview,
  fetchChromaCollections,
  fetchKnowledgeBaseStatus,
  type ChromaCollectionPreview,
  type ChromaCollectionSummary
} from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

export function KnowledgeBasePage({ onClose }: { onClose: () => void }) {
  const [status, setStatus] = useState<Awaited<ReturnType<typeof fetchKnowledgeBaseStatus>> | null>(null);
  const [collections, setCollections] = useState<ChromaCollectionSummary[]>([]);
  const [selectedCollection, setSelectedCollection] = useState("");
  const [collectionPreview, setCollectionPreview] = useState<ChromaCollectionPreview | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  async function refreshAll() {
    setLoading(true);
    setError("");
    try {
      const [nextStatus, nextCollections] = await Promise.all([
        fetchKnowledgeBaseStatus(),
        fetchChromaCollections(),
      ]);
      setStatus(nextStatus);
      setCollections(nextCollections);
      const nextSelected =
        nextCollections.find((item) => item.name === selectedCollection)?.name ??
        nextCollections[0]?.name ??
        "";
      setSelectedCollection(nextSelected);
      if (nextSelected) {
        setCollectionPreview(await fetchChromaCollectionPreview(nextSelected));
      } else {
        setCollectionPreview(null);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not load project collections.");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void refreshAll();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  async function handleSelectCollection(collectionName: string) {
    setSelectedCollection(collectionName);
    setCollectionPreview(await fetchChromaCollectionPreview(collectionName));
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <div className="text-2xl font-semibold tracking-tight">Project Collections</div>
          <div className="mt-1 text-sm text-muted-foreground">
            Inspect project-scoped vector collections only. Shared knowledge-base uploads have been retired.
          </div>
        </div>
        <Button variant="outline" onClick={onClose}>
          Back to Studio
        </Button>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Project Retrieval Status</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="rounded-[16px] border border-slate-200 bg-slate-50 px-4 py-3 text-sm text-slate-700">
            <div>
              <span className="font-semibold text-slate-900">Project collections:</span> {status?.collection_count ?? 0}
            </div>
            <div>
              <span className="font-semibold text-slate-900">Stored chunks:</span> {status?.chunk_count ?? 0}
            </div>
            <div>
              <span className="font-semibold text-slate-900">Indexed:</span> {status?.indexed ? "Yes" : "No"}
            </div>
            {status?.reason ? <div className="mt-1 text-xs text-slate-500">{status.reason}</div> : null}
          </div>

          {error ? <div className="text-sm text-red-600">{error}</div> : null}

          <div className="flex flex-wrap gap-3">
            <Button disabled={loading} variant="outline" onClick={() => void refreshAll()}>
              {loading ? "Refreshing..." : "Refresh"}
            </Button>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader className="gap-3">
          <CardTitle>Chroma Explorer</CardTitle>
          <div className="text-sm text-muted-foreground">
            Inspect the local project-scoped vector collections, stored chunks, and chunk metadata.
          </div>
        </CardHeader>
        <CardContent className="space-y-4">
          {collections.length === 0 ? (
            <div className="rounded-[24px] border border-dashed border-border p-4 text-sm text-muted-foreground">
              No project collections are visible yet. Run Generate or Validate with a project name and supporting
              attachments to create one.
            </div>
          ) : (
            <div className="flex flex-wrap gap-2">
              {collections.map((item) => (
                <button
                  key={item.name}
                  type="button"
                  className={`rounded-full border px-3 py-1.5 text-sm font-medium transition ${
                    selectedCollection === item.name
                      ? "border-slate-900 bg-slate-900 text-white"
                      : "border-slate-200 bg-white text-slate-700 hover:border-slate-300"
                  }`}
                  onClick={() => void handleSelectCollection(item.name)}
                >
                  {item.name} ({item.chunk_count})
                </button>
              ))}
            </div>
          )}

          {collectionPreview ? (
            <div className="space-y-3">
              <div className="rounded-[20px] border border-slate-200 bg-slate-50 px-4 py-3 text-sm text-slate-700">
                <span className="font-semibold text-slate-900">Collection:</span> {collectionPreview.collection}
                <span className="ml-4 font-semibold text-slate-900">Chunks:</span> {collectionPreview.chunk_count}
              </div>
              {collectionPreview.items.length === 0 ? (
                <div className="rounded-[24px] border border-dashed border-border p-4 text-sm text-muted-foreground">
                  This collection exists but currently has no previewable chunks.
                </div>
              ) : (
                collectionPreview.items.map((item) => (
                  <div
                    key={item.id}
                    className="rounded-[24px] border border-white/70 bg-white/85 p-4 text-sm text-slate-700 shadow-sm"
                  >
                    <div className="text-sm font-semibold text-slate-900">{item.id}</div>
                    <div className="mt-2 rounded-[16px] bg-slate-50 px-3 py-3 text-sm leading-6 text-slate-700">
                      {item.document_preview || "No preview text available."}
                    </div>
                    <div className="mt-3 overflow-x-auto">
                      <table className="w-full min-w-[520px] border-collapse overflow-hidden rounded-[16px]">
                        <thead className="bg-slate-100">
                          <tr>
                            <th className="border border-slate-200 px-3 py-2 text-left text-xs font-semibold uppercase tracking-[0.12em] text-slate-600">
                              Metadata Key
                            </th>
                            <th className="border border-slate-200 px-3 py-2 text-left text-xs font-semibold uppercase tracking-[0.12em] text-slate-600">
                              Value
                            </th>
                          </tr>
                        </thead>
                        <tbody>
                          {Object.entries(item.metadata ?? {}).map(([key, value]) => (
                            <tr key={`${item.id}-${key}`} className="bg-white">
                              <td className="border border-slate-200 px-3 py-2 align-top text-sm text-slate-800">
                                {key}
                              </td>
                              <td className="border border-slate-200 px-3 py-2 align-top text-sm text-slate-700">
                                {String(value ?? "")}
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  </div>
                ))
              )}
            </div>
          ) : null}
        </CardContent>
      </Card>
    </div>
  );
}
