"use client";

import { useEffect, useRef, useState } from "react";
import { Send, Loader2, Bot, User, AlertCircle } from "lucide-react";
import { streamAnswer } from "@/lib/api";

interface Message {
  id: string;
  role: "user" | "assistant";
  content: string;
  streaming?: boolean;
  error?: boolean;
}

const EXAMPLE_QUESTIONS = [
  "What is our current revenue trend?",
  "Which departments are underperforming?",
  "What were the key risks last quarter?",
  "What is our strategic outlook for next year?",
  "How is customer satisfaction trending?",
];

export default function ChatInterface({ agentReady }: { agentReady: boolean }) {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [isStreaming, setIsStreaming] = useState(false);
  const bottomRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  function autoResize() {
    const ta = textareaRef.current;
    if (!ta) return;
    ta.style.height = "auto";
    ta.style.height = `${Math.min(ta.scrollHeight, 160)}px`;
  }

  async function sendMessage(question: string) {
    if (!question.trim() || isStreaming) return;
    setInput("");
    if (textareaRef.current) textareaRef.current.style.height = "auto";

    const userMsg: Message = { id: Date.now().toString(), role: "user", content: question };
    const assistantId = (Date.now() + 1).toString();
    const assistantMsg: Message = { id: assistantId, role: "assistant", content: "", streaming: true };

    setMessages((prev) => [...prev, userMsg, assistantMsg]);
    setIsStreaming(true);

    try {
      for await (const chunk of streamAnswer(question)) {
        setMessages((prev) =>
          prev.map((m) =>
            m.id === assistantId ? { ...m, content: m.content + chunk } : m
          )
        );
      }
      setMessages((prev) =>
        prev.map((m) => (m.id === assistantId ? { ...m, streaming: false } : m))
      );
    } catch (err) {
      const detail = err instanceof Error ? err.message : "Something went wrong";
      setMessages((prev) =>
        prev.map((m) =>
          m.id === assistantId
            ? { ...m, content: detail, streaming: false, error: true }
            : m
        )
      );
    } finally {
      setIsStreaming(false);
    }
  }

  function handleKeyDown(e: React.KeyboardEvent<HTMLTextAreaElement>) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      sendMessage(input);
    }
  }

  return (
    <div className="flex flex-col h-full">
      {/* Messages */}
      <div className="flex-1 overflow-y-auto custom-scroll px-4 py-6 space-y-6">
        {messages.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-full gap-6 text-center">
            <div className="w-14 h-14 rounded-2xl bg-indigo-600/20 border border-indigo-500/30 flex items-center justify-center">
              <Bot size={28} className="text-indigo-400" />
            </div>
            <div>
              <h1 className="text-xl font-semibold text-gray-200">AI Leadership Insight Agent</h1>
              <p className="text-sm text-gray-500 mt-1">
                {agentReady
                  ? "Ask anything about your company documents."
                  : "Upload documents in the panel to get started."}
              </p>
            </div>
            {agentReady && (
              <div className="grid grid-cols-1 gap-2 w-full max-w-lg">
                {EXAMPLE_QUESTIONS.map((q) => (
                  <button
                    key={q}
                    onClick={() => sendMessage(q)}
                    className="text-left px-4 py-2.5 rounded-xl border border-gray-800 bg-gray-900 hover:border-indigo-500/50 hover:bg-gray-800 text-sm text-gray-400 hover:text-gray-200 transition-all"
                  >
                    {q}
                  </button>
                ))}
              </div>
            )}
          </div>
        ) : (
          messages.map((msg) => (
            <div key={msg.id} className={`flex gap-3 ${msg.role === "user" ? "justify-end" : "justify-start"}`}>
              {msg.role === "assistant" && (
                <div className="w-7 h-7 rounded-lg bg-indigo-600/20 border border-indigo-500/30 flex items-center justify-center shrink-0 mt-0.5">
                  <Bot size={14} className="text-indigo-400" />
                </div>
              )}
              <div
                className={`max-w-[75%] rounded-2xl px-4 py-3 text-sm leading-relaxed whitespace-pre-wrap ${
                  msg.role === "user"
                    ? "bg-indigo-600 text-white rounded-tr-sm"
                    : msg.error
                    ? "bg-red-900/30 border border-red-500/30 text-red-300 rounded-tl-sm"
                    : "bg-gray-800 text-gray-200 rounded-tl-sm"
                }`}
              >
                {msg.error && <AlertCircle size={14} className="inline mr-1.5 mb-0.5" />}
                {msg.content}
                {msg.streaming && <span className="cursor-blink" />}
              </div>
              {msg.role === "user" && (
                <div className="w-7 h-7 rounded-lg bg-gray-700 flex items-center justify-center shrink-0 mt-0.5">
                  <User size={14} className="text-gray-300" />
                </div>
              )}
            </div>
          ))
        )}
        <div ref={bottomRef} />
      </div>

      {/* Input bar */}
      <div className="border-t border-gray-800 p-4">
        <div className="flex items-end gap-3 bg-gray-900 border border-gray-700 rounded-2xl px-4 py-3 focus-within:border-indigo-500/50 transition-colors">
          <textarea
            ref={textareaRef}
            value={input}
            onChange={(e) => { setInput(e.target.value); autoResize(); }}
            onKeyDown={handleKeyDown}
            placeholder={agentReady ? "Ask a leadership question… (Enter to send)" : "Upload documents first…"}
            disabled={!agentReady || isStreaming}
            rows={1}
            className="flex-1 bg-transparent resize-none text-sm text-gray-200 placeholder-gray-600 focus:outline-none disabled:opacity-50 max-h-40"
          />
          <button
            onClick={() => sendMessage(input)}
            disabled={!agentReady || isStreaming || !input.trim()}
            className="w-8 h-8 rounded-xl bg-indigo-600 hover:bg-indigo-500 disabled:opacity-40 disabled:cursor-not-allowed flex items-center justify-center transition-colors shrink-0"
          >
            {isStreaming ? (
              <Loader2 size={15} className="animate-spin text-white" />
            ) : (
              <Send size={15} className="text-white" />
            )}
          </button>
        </div>
        <p className="text-xs text-gray-700 text-center mt-2">
          Shift+Enter for new line
        </p>
      </div>
    </div>
  );
}
