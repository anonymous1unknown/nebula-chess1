import { useEffect, useMemo, useRef, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { api, getToken } from "../lib/api";
import Board from "../components/Board";
import { motion } from "framer-motion";
import { Copy, RefreshCcw, MessageSquare, Brain, ShieldAlert, Volume2 } from "lucide-react";

export default function GamePage() {
  const { gameId } = useParams();
  const nav = useNavigate();
  const [state, setState] = useState<any>(null);
  const [moves, setMoves] = useState<any[]>([]);
  const [analysis, setAnalysis] = useState<any>(null);
  const [chat, setChat] = useState("");
  const [selected, setSelected] = useState<string | null>(null);
  const wsRef = useRef<WebSocket | null>(null);

  useEffect(() => {
    if (!gameId) return;
    api.getGame(gameId).then(setState);
    api.getMoves(gameId).then(setMoves).catch(() => {});
    const ws = new WebSocket(`${api.API.replace("http", "ws")}/ws/games/${gameId}?token=${getToken()}`);
    wsRef.current = ws;
    ws.onmessage = (evt) => {
      const msg = JSON.parse(evt.data);
      if (msg.type === "state") setState(msg.state);
      if (msg.type === "chat") setMoves((m) => m);
    };
    return () => ws.close();
  }, [gameId]);

  const sendMove = (from: string, to: string) => {
    if (!wsRef.current || wsRef.current.readyState !== WebSocket.OPEN) return;
    wsRef.current.send(JSON.stringify({ type: "move", uci: `${from}${to}` }));
    setSelected(null);
  };

  const sendChat = () => {
    if (!wsRef.current || wsRef.current.readyState !== WebSocket.OPEN || !chat.trim()) return;
    wsRef.current.send(JSON.stringify({ type: "chat", content: chat.trim() }));
    setChat("");
  };

  const side = state?.white_id && state?.black_id ? "white" : "white";

  if (!state) return <div className="panel">Loading game...</div>;

  return (
    <div className="game-grid">
      <section className="panel board-panel">
        <div className="panel-head">
          <div>
            <h2>Game #{gameId?.slice(0, 8)}</h2>
            <p>{state.status} · turn {state.turn === "w" ? "white" : "black"} · spectators {state.spectators}</p>
          </div>
          <div className="panel-actions">
            <button className="icon-btn" onClick={() => navigator.clipboard.writeText(`${window.location.origin}/#/game/${gameId}`)}><Copy size={16} /></button>
            <button className="icon-btn" onClick={() => nav(`/analysis/${gameId}`)}><Brain size={16} /></button>
          </div>
        </div>

        <div className="board-shell">
          <Board fen={state.current_fen} legalMoves={state.legal_moves || []} onMove={sendMove} orientation="white" selectedSquare={selected} onSelectSquare={setSelected} />
          <aside className="sidepanels">
            <div className="glass">
              <h3>Clocks</h3>
              <div className="clock-row"><span>White</span><strong>{Math.ceil((state.white_clock_ms||0)/1000)}s</strong></div>
              <div className="clock-row"><span>Black</span><strong>{Math.ceil((state.black_clock_ms||0)/1000)}s</strong></div>
            </div>
            <div className="glass">
              <h3>Move list</h3>
              <div className="move-list">
                {moves.map((m) => <div key={m.ply} className="move-line"><span>{m.ply}.</span><strong>{m.san}</strong></div>)}
              </div>
            </div>
          </aside>
        </div>

        <div className="toolbar">
          <button className="secondary" onClick={() => api.rematch(gameId!).then((g) => nav(`/game/${g.id}`))}><RefreshCcw size={16} /> Rematch</button>
          <button className="secondary" onClick={() => api.analysis(gameId!).then(setAnalysis)}><Brain size={16} /> Analyze</button>
        </div>
        {analysis && <div className="analysis-strip">Eval: {analysis.evaluation_cp ?? "n/a"} · Best: {analysis.best_move ?? "n/a"} · Cheat score: {analysis.cheat_score?.toFixed(2) ?? "n/a"} — {analysis.cheat_reason}</div>}
      </section>

      <section className="panel chat-panel">
        <h3>Live chat</h3>
        <div className="chat-box">
          <p className="muted">Realtime chat is connected through the authoritative room channel.</p>
        </div>
        <div className="chat-input">
          <input value={chat} onChange={(e) => setChat(e.target.value)} placeholder="Say something..." />
          <button onClick={sendChat}><MessageSquare size={16} /></button>
        </div>
        <div className="glass warning">
          <ShieldAlert size={16} /> Anti-cheat signals are logged server-side and routed to review, not blind bans.
        </div>
      </section>
    </div>
  );
}
