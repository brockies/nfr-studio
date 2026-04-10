import { FormEvent, useState } from "react";

import { SendHorizonal } from "lucide-react";

import { MarkdownPanel } from "@/components/markdown-panel";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Textarea } from "@/components/ui/textarea";
import { askFollowUp } from "@/lib/api";
import type { ChatMessage, RunPayload } from "@/types";

export function FollowUpChat({
  run,
  messages,
  onMessagesChange
}: {
  run: RunPayload;
  messages: ChatMessage[];
  onMessagesChange: (messages: ChatMessage[]) => void;
}) {
  const [question, setQuestion] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    if (!question.trim()) {
      return;
    }

    const userMessage: ChatMessage = { role: "user", content: question.trim() };
    const nextMessages: ChatMessage[] = [...messages, userMessage];
    onMessagesChange(nextMessages);
    setSubmitting(true);
    setError("");

    try {
      const response = await askFollowUp(run, question.trim(), nextMessages.slice(0, -1));
      const assistantMessage: ChatMessage = {
        role: "assistant",
        content: response.answer,
      };
      onMessagesChange([...nextMessages, assistantMessage]);
      setQuestion("");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Follow-up request failed.");
      onMessagesChange(messages);
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>Ask About This Run</CardTitle>
        <p className="text-sm text-muted-foreground">
          Grounded follow-up questions use the current run only and do not invent extra system detail.
        </p>
      </CardHeader>
      <CardContent className="space-y-4">
        {messages.length === 0 ? (
          <div className="rounded-[24px] border border-dashed border-border bg-background/60 p-4 text-sm text-muted-foreground">
            Try asking: Which NFRs matter most for MVP? What should I clarify with stakeholders next? Rewrite the security NFRs more tightly.
          </div>
        ) : (
          <div className="space-y-4">
            {messages.map((message, index) => (
              <div
                key={`${message.role}-${index}`}
                className={`rounded-[24px] p-4 ${
                  message.role === "assistant" ? "bg-white" : "bg-sky-50"
                }`}
              >
                <div className="mb-2 text-xs font-semibold uppercase tracking-[0.2em] text-muted-foreground">
                  {message.role}
                </div>
                <MarkdownPanel content={message.content} />
              </div>
            ))}
          </div>
        )}

        <form className="space-y-3" onSubmit={handleSubmit}>
          <Textarea
            value={question}
            onChange={(event) => setQuestion(event.target.value)}
            placeholder="Ask about this NFR pack..."
            className="min-h-[110px]"
          />
          {error ? <div className="text-sm text-destructive">{error}</div> : null}
          <div className="flex items-center justify-between gap-3">
            <Button variant="ghost" type="button" onClick={() => onMessagesChange([])}>
              Clear chat
            </Button>
            <Button disabled={submitting || !question.trim()} type="submit">
              <SendHorizonal className="mr-2 h-4 w-4" />
              {submitting ? "Thinking..." : "Ask"}
            </Button>
          </div>
        </form>
      </CardContent>
    </Card>
  );
}
