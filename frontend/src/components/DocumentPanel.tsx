"use client";

import { useRef, useState } from "react";
import { FileText, Trash2, Upload, Loader2, AlertCircle } from "lucide-react";
import { deleteDocument, uploadDocument } from "@/lib/api";

interface Props {
  documents: string[];
  onRefresh: () => void;
}

export default function DocumentPanel({ documents, onRefresh }: Props) {
  const inputRef = useRef<HTMLInputElement>(null);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [deletingFile, setDeletingFile] = useState<string | null>(null);

  async function handleUpload(e: React.ChangeEvent<HTMLInputElement>) {
    const files = Array.from(e.target.files ?? []);
    if (!files.length) return;
    setUploading(true);
    setError(null);
    try {
      for (const file of files) {
        await uploadDocument(file);
      }
      onRefresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Upload failed");
    } finally {
      setUploading(false);
      if (inputRef.current) inputRef.current.value = "";
    }
  }

  async function handleDelete(filename: string) {
    setDeletingFile(filename);
    setError(null);
    try {
      await deleteDocument(filename);
      onRefresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Delete failed");
    } finally {
      setDeletingFile(null);
    }
  }

  return (
    <aside className="flex flex-col h-full bg-gray-900 border-r border-gray-800">
      {/* Header */}
      <div className="p-4 border-b border-gray-800">
        <h2 className="text-sm font-semibold text-gray-400 uppercase tracking-wider mb-3">
          Documents
        </h2>
        <button
          onClick={() => inputRef.current?.click()}
          disabled={uploading}
          className="w-full flex items-center justify-center gap-2 px-3 py-2 rounded-lg bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 disabled:cursor-not-allowed text-sm font-medium transition-colors"
        >
          {uploading ? (
            <Loader2 size={15} className="animate-spin" />
          ) : (
            <Upload size={15} />
          )}
          {uploading ? "Uploading…" : "Upload Document"}
        </button>
        <input
          ref={inputRef}
          type="file"
          multiple
          accept=".txt,.md,.pdf,.docx"
          className="hidden"
          onChange={handleUpload}
        />
        {error && (
          <div className="mt-2 flex items-start gap-1.5 text-xs text-red-400">
            <AlertCircle size={13} className="mt-0.5 shrink-0" />
            <span>{error}</span>
          </div>
        )}
        <p className="mt-2 text-xs text-gray-600">
          Supports .txt .md .pdf .docx
        </p>
      </div>

      {/* File list */}
      <div className="flex-1 overflow-y-auto custom-scroll p-2">
        {documents.length === 0 ? (
          <p className="text-xs text-gray-600 text-center mt-6 px-4">
            No documents yet. Upload one to get started.
          </p>
        ) : (
          <ul className="space-y-1">
            {documents.map((doc) => (
              <li
                key={doc}
                className="flex items-center gap-2 px-2 py-2 rounded-lg hover:bg-gray-800 group transition-colors"
              >
                <FileText size={14} className="text-indigo-400 shrink-0" />
                <span className="flex-1 text-xs text-gray-300 truncate" title={doc}>
                  {doc}
                </span>
                <button
                  onClick={() => handleDelete(doc)}
                  disabled={deletingFile === doc}
                  className="opacity-0 group-hover:opacity-100 text-gray-600 hover:text-red-400 disabled:opacity-50 transition-all"
                  title="Delete"
                >
                  {deletingFile === doc ? (
                    <Loader2 size={13} className="animate-spin" />
                  ) : (
                    <Trash2 size={13} />
                  )}
                </button>
              </li>
            ))}
          </ul>
        )}
      </div>
    </aside>
  );
}
