import { ShieldAlert, ShieldCheck } from "lucide-react";

import { Card, CardContent } from "@/components/ui/card";
import type { RedactionPreview } from "@/types";

export function RedactionSummary({
  label,
  preview
}: {
  label: string;
  preview: RedactionPreview | null;
}) {
  if (!preview) {
    return null;
  }

  const Icon = preview.changed ? ShieldAlert : ShieldCheck;

  return (
    <Card className={preview.changed ? "border-red-200 bg-red-50/90" : "border-slate-200 bg-slate-50/90"}>
      <CardContent className="p-4">
        <div className="flex items-start gap-3">
          <Icon
            className={`mt-0.5 h-4 w-4 shrink-0 ${
              preview.changed ? "text-red-700" : "text-slate-600"
            }`}
          />
          <div className="space-y-2 text-sm">
            <div className={preview.changed ? "text-red-800" : "text-slate-700"}>
              <span className="font-semibold">{label}:</span> {preview.summary}
            </div>
            {preview.items.length > 0 ? (
              <ul className={preview.changed ? "list-disc pl-5 text-red-800" : "list-disc pl-5 text-slate-700"}>
                {preview.items.map((item) => (
                  <li key={item}>{item}</li>
                ))}
              </ul>
            ) : null}
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
