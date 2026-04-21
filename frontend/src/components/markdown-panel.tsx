import type { ComponentPropsWithoutRef } from "react";

import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

const PLANTUML_SERVER_URL = (import.meta.env.VITE_PLANTUML_SERVER_URL ?? "").trim();

function encodePlantUmlHex(source: string): string {
  const bytes = new TextEncoder().encode(source);
  return `~h${Array.from(bytes, (byte) => byte.toString(16).padStart(2, "0")).join("")}`;
}

function PlantUmlBlock({ source }: { source: string }) {
  const trimmed = source.trim();
  const hasRenderer = Boolean(PLANTUML_SERVER_URL);
  const renderUrl = hasRenderer
    ? `${PLANTUML_SERVER_URL.replace(/\/+$/, "")}/svg/${encodePlantUmlHex(trimmed)}`
    : "";

  return (
    <div className="my-5 space-y-3">
      {hasRenderer ? (
        <div className="overflow-hidden rounded-[24px] border border-slate-200 bg-white shadow-sm">
          <div className="border-b border-slate-200 bg-slate-50 px-4 py-2 text-xs font-semibold uppercase tracking-[0.14em] text-slate-500">
            Rendered Diagram
          </div>
          <div className="overflow-x-auto p-4">
            <img
              alt="Rendered PlantUML diagram"
              className="mx-auto block h-auto w-full max-w-full object-contain"
              loading="lazy"
              src={renderUrl}
            />
          </div>
        </div>
      ) : (
        <div className="rounded-[20px] border border-amber-200 bg-amber-50 px-4 py-3 text-sm leading-6 text-amber-900">
          PlantUML rendering is not configured yet. Set `VITE_PLANTUML_SERVER_URL` to a trusted
          PlantUML server to render the diagram visually; the source is still shown below.
        </div>
      )}

      <details className="rounded-[20px] border border-slate-200 bg-slate-950 text-slate-100">
        <summary className="cursor-pointer select-none px-4 py-3 text-sm font-semibold text-slate-100">
          View PlantUML source
        </summary>
        <pre className="overflow-x-auto px-4 pb-4 pt-0 text-sm leading-6 text-slate-100">
          <code>{trimmed}</code>
        </pre>
      </details>
    </div>
  );
}

function CodeBlock(props: ComponentPropsWithoutRef<"code"> & { className?: string }) {
  const className = props.className ?? "";
  const match = /language-([\w-]+)/.exec(className);
  const language = (match?.[1] ?? "").toLowerCase();
  const content = String(props.children ?? "").replace(/\n$/, "");

  if (language === "plantuml") {
    return <PlantUmlBlock source={content} />;
  }

  return (
    <code className={className}>
      {props.children}
    </code>
  );
}

export function MarkdownPanel({ content }: { content: string }) {
  return (
    <div
      className="max-w-none text-[15px] leading-8 text-slate-700
        [&>*:first-child]:mt-0
        [&>*:last-child]:mb-0
        [&_h1]:mt-8 [&_h1]:text-3xl [&_h1]:font-semibold [&_h1]:tracking-tight [&_h1]:text-slate-900
        [&_h2]:mt-8 [&_h2]:text-2xl [&_h2]:font-semibold [&_h2]:tracking-tight [&_h2]:text-slate-900
        [&_h3]:mt-6 [&_h3]:text-lg [&_h3]:font-semibold [&_h3]:text-slate-900
        [&_h4]:mt-5 [&_h4]:text-base [&_h4]:font-semibold [&_h4]:text-slate-900
        [&_p]:my-3 [&_p]:leading-8
        [&_strong]:font-semibold [&_strong]:text-slate-900
        [&_ul]:my-4 [&_ul]:list-disc [&_ul]:space-y-2 [&_ul]:pl-6
        [&_ol]:my-4 [&_ol]:list-decimal [&_ol]:space-y-2 [&_ol]:pl-6
        [&_li]:pl-1 [&_li]:leading-8
        [&_blockquote]:my-5 [&_blockquote]:border-l-4 [&_blockquote]:border-sky-200 [&_blockquote]:bg-sky-50/60 [&_blockquote]:px-4 [&_blockquote]:py-3 [&_blockquote]:italic
        [&_hr]:my-8 [&_hr]:border-slate-200
        [&_code]:rounded [&_code]:bg-slate-100 [&_code]:px-1.5 [&_code]:py-0.5 [&_code]:text-[0.95em]
        [&_pre]:my-5 [&_pre]:overflow-x-auto [&_pre]:rounded-2xl [&_pre]:bg-slate-950 [&_pre]:p-4 [&_pre]:text-sm [&_pre]:leading-6 [&_pre]:text-slate-100
        [&_pre_code]:bg-transparent [&_pre_code]:p-0 [&_pre_code]:text-inherit
        [&_table]:my-5 [&_table]:w-full [&_table]:border-collapse [&_table]:overflow-hidden [&_table]:rounded-2xl
        [&_thead]:bg-slate-100
        [&_th]:border [&_th]:border-slate-200 [&_th]:px-3 [&_th]:py-2 [&_th]:text-left [&_th]:text-sm [&_th]:font-semibold [&_th]:text-slate-900
        [&_td]:border [&_td]:border-slate-200 [&_td]:px-3 [&_td]:py-2 [&_td]:align-top [&_td]:text-sm [&_td]:leading-6"
    >
      <ReactMarkdown
        components={{
          code: CodeBlock,
        }}
        remarkPlugins={[remarkGfm]}
      >
        {content}
      </ReactMarkdown>
    </div>
  );
}
