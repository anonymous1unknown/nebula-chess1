export type UserPublic = {
  id: string;
  email: string;
  username: string;
  display_name?: string | null;
  avatar_url?: string | null;
  rating_blitz: number;
  rating_rapid: number;
  rating_classical: number;
  created_at: string;
};

export type Tokens = {
  access_token: string;
  refresh_token: string;
  token_type: string;
};

export type GameSummary = {
  id: string;
  invite_code: string;
  status: string;
  white_id?: string | null;
  black_id?: string | null;
  current_fen: string;
  result?: string | null;
  created_at: string;
};

export type GameState = {
  game_id: string;
  status: string;
  white_id?: string | null;
  black_id?: string | null;
  current_fen: string;
  pgn: string;
  turn: "w" | "b";
  legal_moves: string[];
  white_clock_ms: number;
  black_clock_ms: number;
  result?: string | null;
  winner_id?: string | null;
  move_count: number;
  spectators: number;
  updated_at?: string | null;
};

export type LeaderboardRow = {
  rank: number;
  user: UserPublic;
  rating: number;
  wins: number;
  losses: number;
  draws: number;
};

export type AnalysisResponse = {
  game_id: string;
  evaluation_cp?: number | null;
  best_move?: string | null;
  principal_variation: string[];
  cheat_score?: number | null;
  cheat_reason?: string | null;
};
