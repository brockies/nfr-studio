import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export function defaultRunFilename(
  mode: "generate" | "validate",
  projectName = "",
  refined = false,
) {
  const ts = new Date().toISOString().replace(/\D/g, "").slice(0, 14);
  const slug = projectName
    .trim()
    .toLowerCase()
    .replace(/[^a-z0-9_-]+/g, "_")
    .replace(/__+/g, "_")
    .replace(/^[_\.]+|[_\.]+$/g, "");
  const prefix = slug ? `${slug}__` : "";
  const middle = refined ? `nfr_${mode}_refined` : `nfr_${mode}`;
  return `${prefix}${middle}_${ts}.md`;
}

export function downloadText(filename: string, content: string) {
  const blob = new Blob([content], { type: "text/markdown;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = filename;
  anchor.click();
  URL.revokeObjectURL(url);
}
