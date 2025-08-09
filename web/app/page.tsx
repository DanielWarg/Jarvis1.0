"use client";
import { useEffect, useRef, useState } from "react";

export default function Page() {
  // WS och status
  const [status, setStatus] = useState<string>("ansluter...");
  const chatWsRef = useRef<WebSocket | null>(null);
  const eventsWsRef = useRef<WebSocket | null>(null);

  // UI-state
  const [voice, setVoice] = useState<boolean>(true);
  const [showChat, setShowChat] = useState<boolean>(false);
  const [messages, setMessages] = useState<string>("");
  const [input, setInput] = useState<string>("");
  const areaRef = useRef<HTMLTextAreaElement | null>(null);
  const [event, setEvent] = useState<{ message: string; snapshotUrl?: string } | null>(null);

  // Röstinmatning (Web Speech API)
  const [listening, setListening] = useState<boolean>(false);
  const recognitionRef = useRef<SpeechRecognition | null>(null);

  // Init WS för chat
  useEffect(() => {
    const host = typeof window !== "undefined" ? window.location.hostname : "127.0.0.1";
    const ws = new WebSocket(`ws://${host}:8000/ws/chat`);
    ws.onopen = () => setStatus("ansluten");
    ws.onclose = () => setStatus("frånkopplad");
    ws.onerror = () => setStatus("fel på anslutning");
    ws.onmessage = (ev) => {
      try {
        const obj = JSON.parse(ev.data);
        if (obj?.done) {
          const secs = obj.total_duration ? (obj.total_duration / 1e9).toFixed(2) : undefined;
          setStatus(secs ? `klar (${secs}s)` : "klar");
          return;
        }
      } catch {}
      setMessages((prev) => (prev ? prev + ev.data : ev.data));
    };
    chatWsRef.current = ws;
    return () => ws.close();
  }, []);

  // Init WS för events (motion, osv.)
  useEffect(() => {
    const host = typeof window !== "undefined" ? window.location.hostname : "127.0.0.1";
    const ws = new WebSocket(`ws://${host}:8000/ws/events`);
    ws.onmessage = (ev) => {
      try {
        const obj = JSON.parse(ev.data);
        if (obj?.message) {
          setEvent({ message: obj.message, snapshotUrl: obj.snapshotUrl });
          if (voice && "speechSynthesis" in window) {
            const u = new SpeechSynthesisUtterance(obj.message);
            speechSynthesis.speak(u);
          }
        }
      } catch {}
    };
    eventsWsRef.current = ws;
    return () => ws.close();
  }, [voice]);

  // Auto-scroll när tokens byggs upp
  useEffect(() => {
    if (areaRef.current) areaRef.current.scrollTop = areaRef.current.scrollHeight;
  }, [messages]);

  // Röstinmatning setup
  useEffect(() => {
    if (typeof window === "undefined") return;
    const SR: any = (window as any).webkitSpeechRecognition || (window as any).SpeechRecognition;
    if (!SR) return;
    const rec: SpeechRecognition = new SR();
    rec.lang = "sv-SE";
    rec.continuous = false;
    rec.interimResults = false;
    rec.onresult = (e: SpeechRecognitionEvent) => {
      const text = e.results?.[0]?.[0]?.transcript;
      if (text) void sendPrompt(text);
    };
    rec.onend = () => setListening(false);
    recognitionRef.current = rec;
  }, []);

  const startVoice = () => {
    if (!recognitionRef.current) return;
    try {
      recognitionRef.current.start();
      setListening(true);
    } catch {}
  };

  const sendPrompt = async (prompt: string) => {
    const host = typeof window !== "undefined" ? window.location.hostname : "127.0.0.1";
    const ws = chatWsRef.current;
    if (!ws || ws.readyState !== WebSocket.OPEN) {
      setStatus("ej ansluten – REST-fallback");
      try {
        const resp = await fetch(`http://${host}:8000/api/chat`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ prompt, model: "gpt-oss:20b", stream: false }),
        });
        const data = await resp.json();
        if (data?.response) setMessages((prev) => prev + data.response);
      } catch {}
      return;
    }
    ws.send(JSON.stringify({ prompt, model: "gpt-oss:20b" }));
  };

  const onSendClick = () => {
    if (!input.trim()) return;
    void sendPrompt(input.trim());
    setInput("");
  };

  const stopStream = () => {
    try {
      chatWsRef.current?.close();
      setStatus("stoppad");
    } catch {}
  };

  return (
    <main className="min-h-screen flex flex-col items-center justify-center p-6 relative">
      {/* Orb */}
      <div className="relative">
        <div className="w-64 h-64 md:w-80 md:h-80 rounded-full bg-gradient-to-br from-blue-500/30 via-purple-500/20 to-cyan-500/30 blur-sm" />
        <div className="absolute inset-0 rounded-full bg-gradient-to-b from-blue-400/30 to-indigo-600/20 animate-pulse" />
        <div className="absolute inset-0 rounded-full border border-white/10" />
      </div>

      {/* Kontroller under orben */}
      <div className="mt-6 flex items-center gap-3">
        <button
          className="px-3 py-2 rounded bg-blue-600 hover:bg-blue-500"
          onClick={startVoice}
          aria-pressed={listening}
        >
          {listening ? "Lyssnar..." : "Tala"}
        </button>
        <button
          className="px-3 py-2 rounded bg-gray-700 hover:bg-gray-600"
          onClick={() => setVoice((v) => !v)}
        >
          {voice ? "Röst: på" : "Röst: av"}
        </button>
        <button
          className="px-3 py-2 rounded bg-gray-800 hover:bg-gray-700 border border-gray-600"
          onClick={() => setShowChat((s) => !s)}
        >
          {showChat ? "Dölj chatt" : "Visa chatt"}
        </button>
        <span className="text-xs text-gray-400">{status}</span>
      </div>

      {/* Popout under sfären */}
      {showChat && (
        <div className="mt-4 w-full max-w-md bg-gray-950 border border-gray-800 rounded p-3 space-y-2">
          <textarea
            ref={areaRef}
            className="w-full h-32 p-2 rounded bg-gray-900 border border-gray-700"
            value={messages}
            readOnly
          />
          <div className="flex gap-2">
            <input
              className="flex-1 p-2 rounded bg-gray-900 border border-gray-700"
              placeholder="Skriv ett meddelande"
              value={input}
              onChange={(e) => setInput(e.target.value)}
            />
            <button className="px-3 py-2 rounded bg-blue-600 hover:bg-blue-500" onClick={onSendClick}>
              Skicka
            </button>
            <button className="px-3 py-2 rounded bg-gray-700 hover:bg-gray-600" onClick={stopStream}>
              Stop
            </button>
          </div>
        </div>
      )}

      {/* Händelseruta (genie) */}
      {event && (
        <div className="fixed bottom-4 right-4 w-64 bg-gray-900 border border-gray-700 rounded shadow-lg p-3 space-y-2">
          <div className="text-sm font-medium">{event.message}</div>
          {event.snapshotUrl && (
            <img src={event.snapshotUrl} alt="snapshot" className="w-full h-auto rounded" />
          )}
        </div>
      )}
    </main>
  );
}


