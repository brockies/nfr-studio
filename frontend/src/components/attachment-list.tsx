import { FileText, ImageIcon, Trash2 } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

function formatBytes(bytes: number) {
  if (bytes < 1024) {
    return `${bytes} B`;
  }
  if (bytes < 1024 * 1024) {
    return `${(bytes / 1024).toFixed(1)} KB`;
  }
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

function isImage(file: File) {
  return file.type.startsWith("image/");
}

export function AttachmentList({
  files,
  onRemove,
  onClear,
}: {
  files: File[];
  onRemove: (index: number) => void;
  onClear: () => void;
}) {
  if (files.length === 0) {
    return null;
  }

  return (
    <Card className="border-slate-200 bg-slate-50/90 shadow-none">
      <CardHeader className="flex-row items-center justify-between gap-3">
        <CardTitle className="text-base">Selected Attachments</CardTitle>
        <Button size="sm" type="button" variant="ghost" onClick={onClear}>
          Clear all
        </Button>
      </CardHeader>
      <CardContent className="space-y-3">
        {files.map((file, index) => {
          const Icon = isImage(file) ? ImageIcon : FileText;

          return (
            <div
              key={`${file.name}-${file.size}-${index}`}
              className="flex items-start justify-between gap-3 rounded-[22px] border border-border bg-white p-4"
            >
              <div className="flex min-w-0 items-start gap-3">
                <div className="mt-0.5 inline-flex h-10 w-10 items-center justify-center rounded-2xl bg-sky-100 text-sky-700">
                  <Icon className="h-4 w-4" />
                </div>
                <div className="min-w-0">
                  <div className="truncate font-semibold text-foreground">{file.name}</div>
                  <div className="mt-1 text-sm text-muted-foreground">
                    {file.type || "Unknown type"} - {formatBytes(file.size)}
                  </div>
                </div>
              </div>
              <Button
                size="sm"
                type="button"
                variant="outline"
                onClick={() => onRemove(index)}
              >
                <Trash2 className="mr-2 h-4 w-4" />
                Remove
              </Button>
            </div>
          );
        })}
      </CardContent>
    </Card>
  );
}
