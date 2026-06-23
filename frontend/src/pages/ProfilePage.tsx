import { useEffect, useState } from "react";
import { api } from "../lib/api";

export default function ProfilePage() {
  const [me, setMe] = useState<any>(null);
  const [history, setHistory] = useState<any[]>([]);
  useEffect(() => {
    api.me().then(setMe).catch(() => {});
    api.myHistory().then(setHistory).catch(() => {});
  }, []);
  if (!me) return <div className="panel">Sign in to view your profile.</div>;
  return (
    <div className="stack">
      <div className="panel">
        <h2>{me.username}</h2>
        <p>{me.display_name || "No display name"} · {me.email}</p>
        <div className="grid-3">
          <div className="metric"><strong>{me.rating_blitz}</strong><span>Blitz</span></div>
          <div className="metric"><strong>{me.rating_rapid}</strong><span>Rapid</span></div>
          <div className="metric"><strong>{me.rating_classical}</strong><span>Classical</span></div>
        </div>
      </div>
      <div className="panel">
        <h3>Recent games</h3>
        {history.map((g) => <div key={g.id} className="history-row"><strong>{g.status}</strong><span>{g.result || "ongoing"}</span></div>)}
      </div>
    </div>
  );
}
