import { PropsWithChildren, useEffect, useState } from "react";
import { Link, NavLink } from "react-router-dom";
import { Crown, LogOut, Menu, MoonStar, SunMedium } from "lucide-react";
import { api, getToken, setTokens } from "../lib/api";

export default function Layout({ children }: PropsWithChildren) {
  const [theme, setTheme] = useState<"dark" | "light">((localStorage.getItem("nebula_theme") as any) || "dark");
  const [me, setMe] = useState<any>(null);
  useEffect(() => {
    document.documentElement.dataset.theme = theme;
    localStorage.setItem("nebula_theme", theme);
  }, [theme]);

  useEffect(() => {
    const token = getToken();
    if (!token) return;
    api.me().then(setMe).catch(() => {});
  }, []);

  return (
    <div className="app-shell">
      <header className="topbar">
        <Link className="brand" to="/">
          <span className="brand-mark">◉</span>
          <span>
            <strong>Nebula Chess</strong>
            <small>premium authority-first platform</small>
          </span>
        </Link>
        <nav className="nav">
          <NavLink to="/">Lobby</NavLink>
          <NavLink to="/leaderboard">Leaderboard</NavLink>
          <NavLink to="/profile">Profile</NavLink>
          <NavLink to="/settings">Settings</NavLink>
        </nav>
        <div className="topbar-actions">
          <button className="icon-btn" onClick={() => setTheme(theme === "dark" ? "light" : "dark")}>
            {theme === "dark" ? <SunMedium size={18} /> : <MoonStar size={18} />}
          </button>
          {me ? <span className="chip"><Crown size={14} /> {me.username}</span> : <span className="chip ghost">Guest</span>}
        </div>
      </header>
      <main className="content">{children}</main>
    </div>
  );
}
