import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import type { CategoryCount } from "@/lib/analysis";

export function CategoryOverview({ items }: { items: CategoryCount[] }) {
  if (items.length === 0) {
    return null;
  }

  const maxCount = Math.max(...items.map((item) => item.count));

  return (
    <Card>
      <CardHeader>
        <CardTitle>NFR Coverage</CardTitle>
        <p className="text-sm text-muted-foreground">
          How the generated requirements are distributed across quality attribute categories.
        </p>
      </CardHeader>
      <CardContent>
        <div className="grid gap-3 md:grid-cols-2">
          {items.map((item) => (
            <div
              key={item.label}
              className="rounded-[24px] border border-border bg-background/80 p-4"
            >
              <div className="flex items-end justify-between gap-3">
                <div className="text-sm font-semibold text-foreground">{item.label}</div>
                <div className="text-2xl font-semibold tracking-tight text-foreground">
                  {item.count}
                </div>
              </div>
              <div className="mt-3 h-2.5 rounded-full bg-slate-200">
                <div
                  className="h-2.5 rounded-full bg-gradient-to-r from-sky-500 to-cyan-300"
                  style={{ width: `${Math.max(12, Math.round((item.count / maxCount) * 100))}%` }}
                />
              </div>
            </div>
          ))}
        </div>
      </CardContent>
    </Card>
  );
}
