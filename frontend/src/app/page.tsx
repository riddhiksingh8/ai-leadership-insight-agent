"use client";

import { useCallback, useEffect, useState } from "react";
import { Brain, Wifi, WifiOff } from "lucide-react";
import DocumentPanel from "@/components/DocumentPanel";
import ChatInterface from "@/components/ChatInterface";
import { fetchDocuments, fetchHealth } from "@/lib/api";

export default function Page() {
  const [documents, setDocuments] = useState<string[]>([]);
  const [agentReady, setAgentReady] = useState(false);
  const [backendOnline, setBackendOnline] = useState<boolean | null>(null);

  const refresh = useCallback(async () => {
    try {
      const [docs, health] = await Promise.all([fetchDocuments(), fetchHealth()]);
      setDocuments(docs);
      setAgentReady(health.agent_ready);
      setBackendOnline(true);
    } catch {
      setBackendOnline(false);
    }
  }, []);

  useEffect(() => {
    refresh();
    const id = setInterval(refresh, 10_000);
    return () => clearInterval(id);
  }, [refresh]);

  return (
    <div className="flex flex-col h-screen">
      {/* Top bar */}
      <header className="flex items-center justify-between px-5 py-3 border-b border-gray-800 bg-gray-950 shrink-0">
        <div className="flex items-center gap-2.5">
          <div className="w-7 h-7 rounded-lg bg-indigo-600/20 border border-indigo-500/30 flex items-center justify-center">
            <Brain size={15} className="text-indigo-400" />
          </div>
          <span className="font-semibold text-sm text-gray-200">AI Leadership Insight Agent</span>
        </div>
        <div className="flex items-center gap-2 text-xs">
          {backendOnline === null ? (
            <span className="text-gray-600">Connecting…</span>
          ) : backendOnline ? (
            <>
              <Wifi size={13} className="text-emerald-500" />
              <span className="text-emerald-500">
                {agentReady ? "Agent ready" : "No documents"}
              </span>
            </>
          ) : (
            <>
              <WifiOff size={13} className="text-red-500" />
              <span className="text-red-500">Backend offline</span>
            </>
          )}
        </div>
      </header>

      {/* Main layout */}
      <div className="flex flex-1 overflow-hidden">
        {/* Left sidebar — documents */}
        <div className="w-64 shrink-0 overflow-hidden">
          <DocumentPanel documents={documents} onRefresh={refresh} />
        </div>

        {/* Right — chat */}
        <main className="flex-1 overflow-hidden">
          <ChatInterface agentReady={agentReady} />
        </main>
      </div>
    </div>
  );
}
