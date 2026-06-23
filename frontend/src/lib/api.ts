import type { AnalysisResponse, GameState, GameSummary, LeaderboardRow, Tokens, UserPublic } from "../types";

const API = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";

export function getToken() {
  return localStorage.getItem("nebula_access_token") || "";
}

export function setTokens(tokens: Tokens) {
  localStorage.setItem("nebula_access_token", tokens.access_token);
  localStorage.setItem("nebula_refresh_token", tokens.refresh_token);
}

async function request<T>(path: string, init: RequestInit = {}, auth = true): Promise<T> {
  const headers = new Headers(init.headers || {});
  headers.set("Content-Type", "application/json");
  if (auth) {
    const token = getToken();
    if (token) headers.set("Authorization", `Bearer ${token}`);
  }
  const res = await fetch(`${API}${path}`, { ...init, headers });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(text || `HTTP ${res.status}`);
  }
  return res.json() as Promise<T>;
}

export const api = {
  API,
  register: (payload: any) => request<Tokens>("/api/auth/register", { method: "POST", body: JSON.stringify(payload) }, false),
  login: (payload: any) => request<Tokens>("/api/auth/login", { method: "POST", body: JSON.stringify(payload) }, false),
  me: () => request<UserPublic>("/api/auth/me"),
  leaderboard: (mode = "blitz") => request<LeaderboardRow[]>(`/api/users/leaderboard?mode=${mode}`),
  myHistory: () => request<any[]>("/api/users/me/history"),
  createGame: (payload: any) => request<GameSummary>("/api/games", { method: "POST", body: JSON.stringify(payload) }),
  joinGame: (invite_code: string) => request<GameSummary>("/api/games/join", { method: "POST", body: JSON.stringify({ invite_code }) }),
  getGame: (gameId: string) => request<GameState>(`/api/games/${gameId}`),
  getMoves: (gameId: string) => request<any[]>(`/api/games/${gameId}/moves`),
  analysis: (gameId: string) => request<AnalysisResponse>(`/api/games/${gameId}/analysis`),
  rematch: (gameId: string) => request<GameSummary>(`/api/games/${gameId}/rematch`, { method: "POST" }),
  chat: (gameId: string, content: string) => request(`/api/games/${gameId}/chat`, { method: "POST", body: JSON.stringify({ content }) }),
};
