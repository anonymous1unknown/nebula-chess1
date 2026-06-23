import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import { api } from "../lib/api";

export default function AnalysisPage() {
  const { gameId } = useParams();
  const [analysis, setAnalysis] = useState<any>(null);
  useEffect(() => { if (gameId) api.analysis(gameId).then(setAnalysis); }, [gameId]);
  if (!analysis) return <div className="panel">Loading analysis...</div>;
  return (
    <div className="panel">
      <h2>Analysis</h2>
      <p>Evaluation: {analysis.evaluation_cp ?? "n/a"}</p>
      <p>Best move: {analysis.best_move ?? "n/a"}</p>
      <p>Cheat score: {analysis.cheat_score?.toFixed(2)}</p>
      <p>{analysis.cheat_reason}</p>
      <pre className="pgn-box">{analysis.principal_variation.join(" ")}</pre>
    </div>
  );
}
