import { useEffect, useState } from "react";
import { Satellite, Send } from "lucide-react";
import UploadArea from "./components/UploadArea";
import ExecutionTrace from "./components/ExecutionTrace";
import { checkHealth, runQuery, uploadImages, type QueryResponse, type UploadResponse } from "./api/client";

type Phase = "idle" | "uploading" | "ready" | "querying" | "done";

export default function App() {
  const [backendUp, setBackendUp] = useState<boolean | null>(null);
  const [files, setFiles] = useState<File[]>([]);
  const [uploadResult, setUploadResult] = useState<UploadResponse | null>(null);
  const [query, setQuery] = useState("");
  const [phase, setPhase] = useState<Phase>("idle");
  const [result, setResult] = useState<QueryResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    checkHealth().then(setBackendUp);
  }, []);

  async function handleUpload() {
    if (files.length === 0) return;
    setPhase("uploading");
    setError(null);
    try {
      const res = await uploadImages(files);
      setUploadResult(res);
      setPhase("ready");
    } catch (e: any) {
      setError(e?.response?.data?.detail || "Upload failed.");
      setPhase("idle");
    }
  }

  async function handleQuery() {
    if (!uploadResult || !query.trim()) return;
    setPhase("querying");
    setError(null);
    setResult(null);
    try {
      const fileIds = uploadResult.files.map((f) => f.file_id);
      const res = await runQuery(fileIds, query);
      setResult(res);
      setPhase("done");
    } catch (e: any) {
      setError(e?.response?.data?.detail || "Query failed.");
      setPhase("ready");
    }
  }

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100">
      <header className="border-b border-slate-800 px-6 py-4">
        <div className="mx-auto flex max-w-4xl items-center gap-3">
          <Satellite className="h-6 w-6 text-cyan-400" />
          <div>
            <h1 className="text-lg font-semibold">SatQuery AI</h1>
            <p className="text-xs text-slate-500">
              PS 26167 — agentic remote-sensing vision-language assistant ·{" "}
              {backendUp === null ? "checking backend…" : backendUp ? (
                <span className="text-emerald-400">backend online</span>
              ) : (
                <span className="text-red-400">backend unreachable</span>
              )}
            </p>
          </div>
        </div>
      </header>

      <main className="mx-auto max-w-4xl space-y-6 px-6 py-8">
        <section className="rounded-lg border border-slate-800 bg-slate-900/40 p-5">
          <h2 className="mb-3 text-sm font-semibold text-slate-300">1. Upload imagery</h2>
          <UploadArea files={files} onChange={setFiles} disabled={phase === "uploading"} />
          <button
            onClick={handleUpload}
            disabled={files.length === 0 || phase === "uploading"}
            className="mt-4 rounded bg-cyan-600 px-4 py-2 text-sm font-medium text-white hover:bg-cyan-500 disabled:cursor-not-allowed disabled:opacity-40"
          >
            {phase === "uploading" ? "Validating…" : "Upload & validate"}
          </button>

          {uploadResult && (
            <div className="mt-4 rounded border border-slate-800 bg-slate-950 p-3 text-xs text-slate-400">
              <div>
                Configuration: <span className="text-slate-200">{uploadResult.input_configuration}</span>
              </div>
              {uploadResult.validation_notes.map((n, i) => (
                <div key={i} className="mt-1">
                  · {n}
                </div>
              ))}
            </div>
          )}
        </section>

        <section className="rounded-lg border border-slate-800 bg-slate-900/40 p-5">
          <h2 className="mb-3 text-sm font-semibold text-slate-300">2. Ask a question</h2>
          <div className="flex gap-2">
            <input
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              disabled={!uploadResult || phase === "querying"}
              placeholder='e.g. "What changed between these images?" or "optical and SAR images — identify built-up areas"'
              className="flex-1 rounded border border-slate-700 bg-slate-950 px-3 py-2 text-sm placeholder:text-slate-600 disabled:opacity-40"
            />
            <button
              onClick={handleQuery}
              disabled={!uploadResult || !query.trim() || phase === "querying"}
              className="flex items-center gap-1 rounded bg-cyan-600 px-4 py-2 text-sm font-medium text-white hover:bg-cyan-500 disabled:cursor-not-allowed disabled:opacity-40"
            >
              <Send className="h-4 w-4" />
              Ask
            </button>
          </div>
        </section>

        {error && (
          <div className="rounded border border-red-900 bg-red-950/50 p-3 text-sm text-red-300">{error}</div>
        )}

        {result && (
          <section className="grid gap-4 md:grid-cols-2">
            <div className="rounded-lg border border-slate-800 bg-slate-900/40 p-5">
              <h2 className="mb-2 text-sm font-semibold text-slate-300">Answer</h2>
              <div className="mb-2 text-xs uppercase tracking-wide text-slate-500">Task: {result.task}</div>
              {result.status === "blocked" ? (
                <div className="rounded border border-amber-900 bg-amber-950/40 p-3 text-sm text-amber-300">
                  Routing and validation succeeded, but no specialist model is
                  integrated for this task in the current environment (see the
                  execution trace and README). This is reported honestly
                  rather than returning a fabricated answer.
                </div>
              ) : (
                <p className="text-sm text-slate-200">{result.answer}</p>
              )}
            </div>
            <ExecutionTrace steps={result.execution_trace} running={phase === "querying"} />
          </section>
        )}
      </main>
    </div>
  );
}
