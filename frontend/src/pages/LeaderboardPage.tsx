import { useEffect, useState } from "react";
import { api } from "../lib/api";

export default function LeaderboardPage() {
  const [rows, setRows] = useState<any[]>([]);
  useEffect(() => { api.leaderboard("blitz").then(setRows); }, []);
  return (
    <div className="panel">
      <h2>Leaderboard</h2>
      {rows.map((r) => (
        <div key={r.user.id} className="leader-row">
          <span>#{r.rank}</span>
          <strong>{r.user.username}</strong>
          <span>{r.rating}</span>
        </div>
      ))}
    </div>
  );
}
