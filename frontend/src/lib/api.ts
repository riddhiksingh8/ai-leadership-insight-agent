const BASE = "/api/backend";

export interface Document {
  name: string;
}

export interface HealthResponse {
  status: string;
  agent_ready: boolean;
  model: string;
}

export async function fetchHealth(): Promise<HealthResponse> {
  const res = await fetch(`${BASE}/health`);
  if (!res.ok) throw new Error("Backend unreachable");
  return res.json();
}

export async function fetchDocuments(): Promise<string[]> {
  const res = await fetch(`${BASE}/documents`);
  if (!res.ok) throw new Error("Failed to fetch documents");
  const data = await res.json();
  return data.documents as string[];
}

export async function uploadDocument(file: File): Promise<void> {
  const form = new FormData();
  form.append("file", file);
  const res = await fetch(`${BASE}/documents/upload`, { method: "POST", body: form });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail ?? "Upload failed");
  }
}

export async function deleteDocument(filename: string): Promise<void> {
  const res = await fetch(`${BASE}/documents/${encodeURIComponent(filename)}`, { method: "DELETE" });
  if (!res.ok) throw new Error("Delete failed");
}

export async function* streamAnswer(question: string, topK = 6): AsyncGenerator<string> {
  const res = await fetch(`${BASE}/ask/stream`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ question, top_k: topK }),
  });

  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail ?? "Failed to get answer");
  }

  const reader = res.body!.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;

    buffer += decoder.decode(value, { stream: true });
    const lines = buffer.split("\n");
    buffer = lines.pop() ?? "";

    for (const line of lines) {
      if (!line.startsWith("data: ")) continue;
      const payload = line.slice(6).trim();
      if (payload === "[DONE]") return;
      try {
        const { text } = JSON.parse(payload);
        if (text) yield text;
      } catch {
        // ignore malformed lines
      }
    }
  }
}
