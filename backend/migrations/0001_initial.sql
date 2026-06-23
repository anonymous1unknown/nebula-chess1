-- Nebula Chess initial schema
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

CREATE TABLE IF NOT EXISTS users (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  email varchar(255) UNIQUE NOT NULL,
  username varchar(32) UNIQUE NOT NULL,
  display_name varchar(80),
  password_hash varchar(255) NOT NULL,
  avatar_url varchar(512),
  bio text,
  country varchar(2),
  rating_blitz integer NOT NULL DEFAULT 1200,
  rating_rapid integer NOT NULL DEFAULT 1200,
  rating_classical integer NOT NULL DEFAULT 1200,
  is_active boolean NOT NULL DEFAULT true,
  is_admin boolean NOT NULL DEFAULT false,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS refresh_tokens (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  jti varchar(64) UNIQUE NOT NULL,
  token_hash varchar(255) NOT NULL,
  expires_at timestamptz NOT NULL,
  revoked_at timestamptz
);
CREATE INDEX IF NOT EXISTS ix_refresh_tokens_user_id ON refresh_tokens(user_id);

CREATE TABLE IF NOT EXISTS games (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  invite_code varchar(32) UNIQUE NOT NULL,
  white_id uuid REFERENCES users(id) ON DELETE SET NULL,
  black_id uuid REFERENCES users(id) ON DELETE SET NULL,
  creator_id uuid REFERENCES users(id) ON DELETE SET NULL,
  status varchar(32) NOT NULL DEFAULT 'waiting',
  variant varchar(32) NOT NULL DEFAULT 'standard',
  time_control_seconds integer NOT NULL DEFAULT 600,
  increment_seconds integer NOT NULL DEFAULT 0,
  initial_fen text NOT NULL DEFAULT 'startpos',
  current_fen text NOT NULL DEFAULT 'startpos',
  pgn text NOT NULL DEFAULT '',
  result varchar(16),
  winner_id uuid REFERENCES users(id) ON DELETE SET NULL,
  turn varchar(1) NOT NULL DEFAULT 'w',
  move_count integer NOT NULL DEFAULT 0,
  white_clock_ms integer NOT NULL DEFAULT 600000,
  black_clock_ms integer NOT NULL DEFAULT 600000,
  last_move_at timestamptz,
  metadata jsonb,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  finished_at timestamptz
);
CREATE INDEX IF NOT EXISTS ix_games_status ON games(status);
CREATE INDEX IF NOT EXISTS ix_games_white_id ON games(white_id);
CREATE INDEX IF NOT EXISTS ix_games_black_id ON games(black_id);
CREATE INDEX IF NOT EXISTS ix_games_created_at ON games(created_at);

CREATE TABLE IF NOT EXISTS moves (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  game_id uuid NOT NULL REFERENCES games(id) ON DELETE CASCADE,
  user_id uuid REFERENCES users(id) ON DELETE SET NULL,
  ply integer NOT NULL,
  move_number integer NOT NULL,
  uci varchar(16) NOT NULL,
  san varchar(16) NOT NULL,
  fen_before text NOT NULL,
  fen_after text NOT NULL,
  duration_ms integer,
  is_legal boolean NOT NULL DEFAULT true,
  created_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS ix_moves_game_ply ON moves(game_id, ply);
CREATE INDEX IF NOT EXISTS ix_moves_game_created_at ON moves(game_id, created_at);

CREATE TABLE IF NOT EXISTS chat_messages (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  game_id uuid NOT NULL REFERENCES games(id) ON DELETE CASCADE,
  sender_id uuid REFERENCES users(id) ON DELETE SET NULL,
  content text NOT NULL,
  is_system boolean NOT NULL DEFAULT false,
  created_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS ix_chat_game_created_at ON chat_messages(game_id, created_at);

CREATE TABLE IF NOT EXISTS friendships (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  friend_id uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  status varchar(24) NOT NULL DEFAULT 'pending',
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT uq_friendship_pair UNIQUE(user_id, friend_id)
);

CREATE TABLE IF NOT EXISTS invitations (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  game_id uuid REFERENCES games(id) ON DELETE CASCADE,
  from_user_id uuid REFERENCES users(id) ON DELETE SET NULL,
  to_user_id uuid REFERENCES users(id) ON DELETE SET NULL,
  code varchar(32) UNIQUE NOT NULL,
  status varchar(24) NOT NULL DEFAULT 'pending',
  expires_at timestamptz NOT NULL,
  created_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS tournaments (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  name varchar(120) NOT NULL,
  description text,
  status varchar(24) NOT NULL DEFAULT 'scheduled',
  starts_at timestamptz,
  ends_at timestamptz,
  created_by uuid REFERENCES users(id) ON DELETE SET NULL,
  created_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS achievements (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  code varchar(64) UNIQUE NOT NULL,
  title varchar(120) NOT NULL,
  description text NOT NULL,
  icon varchar(64)
);

CREATE TABLE IF NOT EXISTS user_achievements (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  achievement_id uuid NOT NULL REFERENCES achievements(id) ON DELETE CASCADE,
  earned_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS rating_history (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  game_id uuid REFERENCES games(id) ON DELETE SET NULL,
  mode varchar(24) NOT NULL DEFAULT 'blitz',
  old_rating integer NOT NULL,
  new_rating integer NOT NULL,
  delta integer NOT NULL,
  created_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS cheat_flags (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  game_id uuid NOT NULL REFERENCES games(id) ON DELETE CASCADE,
  user_id uuid REFERENCES users(id) ON DELETE SET NULL,
  score double precision NOT NULL DEFAULT 0.0,
  status varchar(24) NOT NULL DEFAULT 'needs_review',
  reason text NOT NULL,
  evidence jsonb,
  created_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS ix_cheat_flags_status_created_at ON cheat_flags(status, created_at);

CREATE TABLE IF NOT EXISTS audit_events (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  actor_user_id uuid REFERENCES users(id) ON DELETE SET NULL,
  game_id uuid REFERENCES games(id) ON DELETE SET NULL,
  event_type varchar(64) NOT NULL,
  severity varchar(16) NOT NULL DEFAULT 'info',
  ip_address varchar(64),
  payload jsonb,
  created_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS ix_audit_events_event_type_created_at ON audit_events(event_type, created_at);
