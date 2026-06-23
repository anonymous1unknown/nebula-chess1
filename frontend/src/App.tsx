import { Routes, Route, Navigate, useLocation, useNavigate } from "react-router-dom";
import { AnimatePresence, motion } from "framer-motion";
import { api, setTokens, getToken } from "./lib/api";
import { useEffect, useMemo, useState } from "react";
import type { GameState, LeaderboardRow, UserPublic } from "./types";
import { Shield, Swords, Trophy, User, Settings, Sparkles, Loader2, LogIn, Link2, Plus, Bot } from "lucide-react";
import Board from "./components/Board";
import Layout from "./components/Layout";
import Lobby from "./pages/Lobby";
import GamePage from "./pages/GamePage";
import ProfilePage from "./pages/ProfilePage";
import LeaderboardPage from "./pages/LeaderboardPage";
import AnalysisPage from "./pages/AnalysisPage";
import SettingsPage from "./pages/SettingsPage";

export default function App() {
  return (
    <Layout>
      <AnimatedRoutes />
    </Layout>
  );
}

function AnimatedRoutes() {
  const location = useLocation();
  return (
    <AnimatePresence mode="wait">
      <motion.div key={location.pathname} initial={{ opacity: 0, y: 14 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -14 }} transition={{ duration: 0.22 }}>
        <Routes location={location}>
          <Route path="/" element={<Lobby />} />
          <Route path="/game/:gameId" element={<GamePage />} />
          <Route path="/profile" element={<ProfilePage />} />
          <Route path="/leaderboard" element={<LeaderboardPage />} />
          <Route path="/analysis/:gameId" element={<AnalysisPage />} />
          <Route path="/settings" element={<SettingsPage />} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </motion.div>
    </AnimatePresence>
  );
}
