import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import type { PriorityRow } from "@/lib/analysis";

const PRIORITY_STYLES: Record<string, string> = {
  CRITICAL: "bg-red-100 text-red-800 border-red-200",
  HIGH: "bg-orange-100 text-orange-800 border-orange-200",
  MEDIUM: "bg-amber-100 text-amber-800 border-amber-200",
  LOW: "bg-emerald-100 text-emerald-800 border-emerald-200",
};

export function PriorityHeatmap({ rows }: { rows: PriorityRow[] }) {
  if (rows.length === 0) {
    return null;
  }

  const cellMap = new Map<string, PriorityRow[]>();
  for (const row of rows) {
    const key = `${row.risk}-${row.complexity}`;
    const items = cellMap.get(key) ?? [];
    items.push(row);
    cellMap.set(key, items);
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>Priority Heatmap</CardTitle>
        <p className="text-sm text-muted-foreground">
          Each NFR is plotted by business risk and implementation complexity.
        </p>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="overflow-x-auto">
          <div className="grid min-w-[780px] grid-cols-[96px_repeat(5,minmax(0,1fr))] gap-2">
            <div />
            {[1, 2, 3, 4, 5].map((complexity) => (
              <div
                key={complexity}
                className="px-2 text-center text-xs font-semibold uppercase tracking-[0.16em] text-muted-foreground"
              >
                Complexity {complexity}
              </div>
            ))}

            {[5, 4, 3, 2, 1].map((risk) => (
              <PriorityHeatmapRow
                key={risk}
                risk={risk}
                cellMap={cellMap}
              />
            ))}
          </div>
        </div>

        <div className="flex flex-wrap gap-2 text-xs font-semibold uppercase tracking-[0.14em]">
          {Object.entries(PRIORITY_STYLES).map(([label, className]) => (
            <span
              key={label}
              className={`rounded-full border px-3 py-1 ${className}`}
            >
              {label}
            </span>
          ))}
        </div>
      </CardContent>
    </Card>
  );
}

function PriorityHeatmapRow({
  risk,
  cellMap,
}: {
  risk: number;
  cellMap: Map<string, PriorityRow[]>;
}) {
  return (
    <>
      <div className="flex items-center px-2 text-xs font-semibold uppercase tracking-[0.16em] text-muted-foreground">
        Risk {risk}
      </div>
      {[1, 2, 3, 4, 5].map((complexity) => {
        const items = cellMap.get(`${risk}-${complexity}`) ?? [];
        const tone =
          risk >= 4
            ? "from-red-50 to-red-100"
            : risk === 3
              ? "from-amber-50 to-amber-100"
              : "from-emerald-50 to-emerald-100";

        return (
          <div
            key={`${risk}-${complexity}`}
            className={`min-h-[110px] rounded-[24px] border border-border bg-gradient-to-br ${tone} p-3`}
          >
            <div className="text-xs font-medium text-muted-foreground">
              {items.length} item{items.length === 1 ? "" : "s"}
            </div>
            <div className="mt-3 flex flex-wrap gap-2">
              {items.map((item) => (
                <span
                  key={`${item.id}-${item.priority}`}
                  className={`rounded-full border px-2.5 py-1 text-xs font-semibold ${
                    PRIORITY_STYLES[item.priority] ?? "bg-slate-100 text-slate-800 border-slate-200"
                  }`}
                  title={item.label}
                >
                  {item.id}
                </span>
              ))}
            </div>
          </div>
        );
      })}
    </>
  );
}
