"use client";

import React, { useEffect, useState } from "react";

export default function SpotifyCallbackPage() {
  const [status, setStatus] = useState("Kopplar till Spotify…");
  const [me, setMe] = useState(null);

  useEffect(() => {
    const url = new URL(window.location.href);
    const code = url.searchParams.get("code");
    const error = url.searchParams.get("error");
    if (error) {
      setStatus(`Spotify fel: ${error}`);
      return;
    }
    if (!code) {
      setStatus("Ingen auth-code mottagen");
      return;
    }
    (async () => {
      try {
        // Byt code mot token i backend
        const r = await fetch(`http://127.0.0.1:8000/api/spotify/callback?code=${encodeURIComponent(code)}`);
        const j = await r.json();
        if (!j || !j.ok) {
          setStatus("Tokenutbyte misslyckades");
          return;
        }
        const token = j.token || {};
        const access = token.access_token;
        const refresh = token.refresh_token;
        const expiresInSec = token.expires_in || 3600;
        try { localStorage.setItem("spotify_access_token", access || ""); } catch {}
        try { localStorage.setItem("spotify_refresh_token", refresh || ""); } catch {}
        try { localStorage.setItem("spotify_expires_in", String(Date.now() + expiresInSec * 1000)); } catch {}
        setStatus("Spotify inloggad ✅ (stänger fönstret…)");
        // Hämta profil för bekräftelse
        if (access) {
          const mr = await fetch(`http://127.0.0.1:8000/api/spotify/me?access_token=${encodeURIComponent(access)}`);
          const mj = await mr.json();
          if (mj && mj.ok) setMe(mj.me);
        }
        // Skicka tillbaka till opener om det är en popup
        try {
          if (window.opener && !window.opener.closed) {
            window.opener.postMessage({ kind: 'spotify_auth', ok: true, access_token: access, refresh_token: refresh, me }, '*');
            setTimeout(() => { window.close(); }, 400);
          }
        } catch {}
      } catch {
        setStatus("Ett fel uppstod vid kopplingen");
      }
    })();
  }, []);

  return (
    <div className="min-h-screen bg-[#030b10] text-cyan-100 p-8">
      <h1 className="text-xl font-semibold text-cyan-200">Spotify Callback</h1>
      <p className="mt-2 text-cyan-300/80">{status}</p>
      {me && (
        <div className="mt-4 text-sm text-cyan-200/90">
          <div>Inloggad som: <span className="text-cyan-100 font-semibold">{me.display_name || me.id}</span></div>
          <div className="text-cyan-300/70">{me.email}</div>
        </div>
      )}
      <div className="mt-6">
        <a href="/" className="rounded-xl border border-cyan-400/30 px-3 py-1 text-xs hover:bg-cyan-400/10">Tillbaka till HUD</a>
      </div>
    </div>
  );
}


