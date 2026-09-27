import { CheckCircle2, CircleAlert, CircleSlash, Loader2 } from "lucide-react";
import type { ReactElement } from "react";
import type { ExecutionStep } from "../api/client";

const ICONS: Record<ExecutionStep["status"], ReactElement> = {
  success: <CheckCircle2 className="h-4 w-4 text-emerald-400" />,
  failed: <CircleAlert className="h-4 w-4 text-red-400" />,
  skipped: <CircleSlash className="h-4 w-4 text-slate-500" />,
  not_implemented: <CircleAlert className="h-4 w-4 text-amber-400" />,
};

export default function ExecutionTrace({ steps, running }: { steps: ExecutionStep[]; running: boolean }) {
  return (
    <div className="rounded-lg border border-slate-800 bg-slate-900/60 p-4">
      <h3 className="mb-3 text-xs font-semibold uppercase tracking-wide text-slate-400">Execution trace</h3>
      <ol className="space-y-2">
        {steps.map((s, i) => (
          <li key={i} className="flex items-start gap-2 text-sm">
            {ICONS[s.status]}
            <div>
              <div className="font-medium text-slate-200">
                {s.step.replace(/_/g, " ")}
                {s.model && <span className="ml-2 text-xs text-slate-500">({s.model})</span>}
              </div>
              {s.detail && <div className="text-xs text-slate-500">{s.detail}</div>}
            </div>
          </li>
        ))}
        {running && (
          <li className="flex items-center gap-2 text-sm text-slate-400">
            <Loader2 className="h-4 w-4 animate-spin" />
            Running…
          </li>
        )}
      </ol>
    </div>
  );
}
