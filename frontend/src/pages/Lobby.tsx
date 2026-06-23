import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { api, setTokens, getToken } from "../lib/api";
import { Crown, Sparkles, Swords, Bot, Link2, LogIn, Plus } from "lucide-react";

export default function Lobby() {
  const nav = useNavigate();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [login, setLogin] = useState("");
  const [invite, setInvite] = useState("");
  const [loading, setLoading] = useState(false);
  const [me, setMe] = useState<any>(null);

  useEffect(() => {
    if (getToken()) api.me().then(setMe).catch(() => {});
  }, []);

  async function doRegister() {
    setLoading(true);
    try {
      const tokens = await api.register({ email, username: login || email.split("@")[0], password, display_name: login || undefined });
      setTokens(tokens);
      const user = await api.me();
      setMe(user);
    } finally {
      setLoading(false);
    }
  }

  async function doLogin() {
    setLoading(true);
    try {
      const tokens = await api.login({ login: login || email, password });
      setTokens(tokens);
      const user = await api.me();
      setMe(user);
    } finally {
      setLoading(false);
    }
  }

  async function createGame() {
    const g = await api.createGame({ time_control_seconds: 600, increment_seconds: 5, play_as: "any", against_ai: false, variant: "standard" });
    nav(`/game/${g.id}`);
  }

  async function joinGame() {
    const g = await api.joinGame(invite.trim());
    nav(`/game/${g.id}`);
  }

  async function createAiGame() {
    const g = await api.createGame({ time_control_seconds: 600, increment_seconds: 0, play_as: "white", against_ai: true, variant: "standard" });
    nav(`/game/${g.id}`);
  }

  return (
    <div className="hero-grid">
      <section className="hero-card hero">
        <div className="eyebrow"><Sparkles size={14} /> Nebula Chess</div>
        <h1>Premium chess infrastructure with authority-first multiplayer.</h1>
        <p>Realtime rooms, spectators, timers, analysis, anti-cheat, AI, and polished UX in one cohesive platform.</p>

        <div className="action-row">
          <button className="primary" onClick={createGame}><Plus size={16}/> Create game</button>
          <button className="secondary" onClick={createAiGame}><Bot size={16}/> Play AI</button>
        </div>

        <div className="invite-card">
          <Link2 size={16} />
          <input value={invite} onChange={(e) => setInvite(e.target.value)} placeholder="Paste invite code" />
          <button onClick={joinGame}>Join</button>
        </div>
      </section>

      <section className="hero-card auth">
        <h2>{me ? `Signed in as ${me.username}` : "Sign in"}</h2>
        <input value={login} onChange={(e) => setLogin(e.target.value)} placeholder="Email or username" />
        <input value={email} onChange={(e) => setEmail(e.target.value)} placeholder="Email for register" />
        <input value={password} onChange={(e) => setPassword(e.target.value)} type="password" placeholder="Password" />
        <div className="action-row">
          <button className="primary" disabled={loading} onClick={doLogin}><LogIn size={16}/> Login</button>
          <button className="secondary" disabled={loading} onClick={doRegister}>Register</button>
        </div>
        <div className="stats">
          <div><Crown size={16} /><strong>Live ELO</strong><span>Profiles and leaderboard ready</span></div>
          <div><Swords size={16} /><strong>Realtime</strong><span>WebSocket-authoritative gameplay</span></div>
        </div>
      </section>
    </div>
  );
}
