import { FormEvent, useState } from "react";

import { Eye, LoaderCircle, RefreshCw } from "lucide-react";

import { RedactionSummary } from "@/components/redaction-summary";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Textarea } from "@/components/ui/textarea";
import { useRedactionPreview } from "@/hooks/use-redaction-preview";
import type { RunPayload } from "@/types";

export function RefinementPanel({
  run,
  loading,
  onRefine
}: {
  run: RunPayload;
  loading: boolean;
  onRefine: (additionalContext: string) => Promise<void>;
}) {
  const [showCurrentContext, setShowCurrentContext] = useState(false);
  const [additionalContext, setAdditionalContext] = useState("");
  const [error, setError] = useState("");
  const cannotRefine = run.mode === "validate" && !run.existing_nfrs.trim();
  const preview = useRedactionPreview(additionalContext, !cannotRefine);

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    if (!additionalContext.trim()) {
      setError("Add some extra context before rerunning.");
      return;
    }
    setError("");
    await onRefine(additionalContext.trim());
    setAdditionalContext("");
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>Add More Context</CardTitle>
        <CardDescription>
          Use this when you learn more after the first pass. The app keeps the current context, appends your new information, and reruns as a new version.
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        {cannotRefine ? (
          <div className="rounded-[24px] border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-800">
            This validation run does not include the original NFR input, so it cannot be refined automatically.
          </div>
        ) : null}

        <Button
          variant="outline"
          onClick={() => setShowCurrentContext((current) => !current)}
          type="button"
        >
          <Eye className="mr-2 h-4 w-4" />
          {showCurrentContext ? "Hide current source context" : "Show current source context"}
        </Button>

        {showCurrentContext ? (
          <div className="space-y-3">
            <Textarea value={run.system_description} disabled className="min-h-[160px]" />
            {run.attachment_context ? (
              <Textarea value={run.attachment_context} disabled className="min-h-[160px]" />
            ) : null}
            {run.mode === "validate" ? (
              <Textarea value={run.existing_nfrs} disabled className="min-h-[160px]" />
            ) : null}
          </div>
        ) : null}

        <form className="space-y-4" onSubmit={handleSubmit}>
          <div className="text-sm text-muted-foreground">
            Potential sensitive values are checked automatically and the masked version is used when rerunning.
          </div>
          <Textarea
            value={additionalContext}
            onChange={(event) => setAdditionalContext(event.target.value)}
            className="min-h-[160px]"
            placeholder="Add newly learned constraints, integrations, compliance scope, volume changes, or stakeholder clarifications..."
            disabled={cannotRefine || loading}
          />
          <RedactionSummary label="Additional context" preview={additionalContext.trim() ? preview : null} />
          {error ? <div className="text-sm text-destructive">{error}</div> : null}
          <Button disabled={cannotRefine || loading || !additionalContext.trim()} type="submit">
            {loading ? (
              <>
                <LoaderCircle className="mr-2 h-4 w-4 animate-spin" />
                Rerunning...
              </>
            ) : (
              <>
                <RefreshCw className="mr-2 h-4 w-4" />
                {run.result_source === "loaded" ? "Refine Loaded Run" : "Rerun With More Context"}
              </>
            )}
          </Button>
        </form>
      </CardContent>
    </Card>
  );
}
