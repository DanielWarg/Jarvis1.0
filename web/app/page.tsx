"use client";
import { useEffect, useRef, useState } from "react";

export default function Page() {
  const [messages, setMessages] = useState<string>("");
  const [input, setInput] = useState<string>("");
  const wsRef = useRef<WebSocket | null>(null);

  useEffect(() => {
    const ws = new WebSocket("ws://127.0.0.1:8000/ws/chat");
    ws.onmessage = (ev) => {
      setMessages((prev) => prev + ev.data);
    };
    wsRef.current = ws;
    return () => ws.close();
  }, []);

  const send = () => {
    const payload = JSON.stringify({ prompt: input, model: "gpt-oss:20b" });
    wsRef.current?.send(payload);
  };

  return (
    <main className="max-w-md mx-auto p-4 space-y-4">
      <h1 className="text-xl font-semibold">Jarvis – Chat</h1>
      <textarea
        className="w-full h-24 p-2 rounded bg-gray-900 border border-gray-700"
        value={messages}
        readOnly
      />
      <input
        className="w-full p-2 rounded bg-gray-900 border border-gray-700"
        placeholder="Skriv ett meddelande"
        value={input}
        onChange={(e) => setInput(e.target.value)}
      />
      <button
        className="px-3 py-2 bg-blue-600 rounded hover:bg-blue-500"
        onClick={send}
      >
        Skicka
      </button>
    </main>
  );
}


