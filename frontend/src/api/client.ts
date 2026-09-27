import axios from "axios";

const API_BASE = import.meta.env.VITE_API_URL || "http://localhost:8000/api";

export interface UploadedImageMeta {
  file_id: string;
  filename: string;
  content_type: string;
  size_bytes: number;
  modality: "optical" | "sar" | "unknown";
  format: string;
  width: number | null;
  height: number | null;
  has_geo_metadata: boolean;
  uploaded_at: string;
}

export interface UploadResponse {
  files: UploadedImageMeta[];
  input_configuration: string;
  validation_notes: string[];
}

export interface ExecutionStep {
  step: string;
  status: "success" | "failed" | "skipped" | "not_implemented";
  detail?: string | null;
  model?: string | null;
}

export interface Evidence {
  kind: string;
  file_id?: string | null;
  note?: string | null;
}

export interface QueryResponse {
  task: string;
  answer: string | null;
  confidence: number | null;
  evidence: Evidence[];
  execution_trace: ExecutionStep[];
  status: "completed" | "blocked" | "error";
}

const client = axios.create({ baseURL: API_BASE });

export async function uploadImages(files: File[]): Promise<UploadResponse> {
  const form = new FormData();
  files.forEach((f) => form.append("files", f));
  const { data } = await client.post<UploadResponse>("/upload", form, {
    headers: { "Content-Type": "multipart/form-data" },
  });
  return data;
}

export async function runQuery(fileIds: string[], query: string): Promise<QueryResponse> {
  const { data } = await client.post<QueryResponse>("/query", { file_ids: fileIds, query });
  return data;
}

export async function checkHealth(): Promise<boolean> {
  try {
    const { data } = await client.get("/health");
    return data.status === "ok";
  } catch {
    return false;
  }
}
