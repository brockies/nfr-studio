import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

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
      <ReactMarkdown remarkPlugins={[remarkGfm]}>{content}</ReactMarkdown>
    </div>
  );
}
