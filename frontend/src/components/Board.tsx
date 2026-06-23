import { useMemo, useState } from "react";
import clsx from "clsx";

const files = ["a","b","c","d","e","f","g","h"];
const ranks = ["8","7","6","5","4","3","2","1"];
const pieceMap: Record<string, string> = {
  p: "♟", n: "♞", b: "♝", r: "♜", q: "♛", k: "♚",
  P: "♙", N: "♘", B: "♗", R: "♖", Q: "♕", K: "♔",
};

function parseFenBoard(fen: string) {
  const board = fen.split(" ")[0];
  const rows = board.split("/");
  const grid: string[] = [];
  for (const row of rows) {
    for (const ch of row) {
      if (/\d/.test(ch)) {
        for (let i = 0; i < Number(ch); i++) grid.push("");
      } else grid.push(ch);
    }
  }
  return grid;
}

export default function Board({
  fen,
  legalMoves = [],
  onMove,
  orientation = "white",
  selectedSquare,
  onSelectSquare,
}: {
  fen: string;
  legalMoves?: string[];
  onMove?: (from: string, to: string) => void;
  orientation?: "white" | "black";
  selectedSquare?: string | null;
  onSelectSquare?: (sq: string | null) => void;
}) {
  const grid = useMemo(() => parseFenBoard(fen), [fen]);
  const [dragFrom, setDragFrom] = useState<string | null>(null);
  const squares = orientation === "white" ? [...ranks].flatMap((rank) => files.map((file) => `${file}${rank}`)) : [...ranks].reverse().flatMap((rank) => [...files].reverse().map((file) => `${file}${rank}`));
  const legalTargets = new Set(legalMoves.filter((m) => selectedSquare && m.startsWith(selectedSquare)).map((m) => m.slice(2, 4)));
  const coords = (square: string) => {
    const file = files.indexOf(square[0]);
    const rank = ranks.indexOf(square[1]);
    return rank * 8 + file;
  };

  return (
    <div className="board-wrap">
      <div className="board">
        {squares.map((sq, idx) => {
          const piece = grid[coords(sq)];
          const dark = ((files.indexOf(sq[0]) + ranks.indexOf(sq[1])) % 2) === 1;
          const selected = selectedSquare === sq;
          const canMoveHere = legalTargets.has(sq);
          return (
            <button
              key={sq}
              className={clsx("square", dark && "dark", selected && "selected", canMoveHere && "target")}
              onClick={() => {
                if (!selectedSquare) onSelectSquare?.(sq);
                else if (selectedSquare === sq) onSelectSquare?.(null);
                else if (canMoveHere) onMove?.(selectedSquare, sq);
                else onSelectSquare?.(sq);
              }}
              onDragOver={(e) => e.preventDefault()}
              onDrop={(e) => {
                e.preventDefault();
                const from = e.dataTransfer.getData("text/plain");
                if (from && from !== sq) onMove?.(from, sq);
                setDragFrom(null);
              }}
              onDragStart={(e) => {
                e.dataTransfer.setData("text/plain", sq);
                setDragFrom(sq);
                onSelectSquare?.(sq);
              }}
              draggable={!!piece}
            >
              <span className={clsx("square-label", selected && "visible")}>{sq}</span>
              {canMoveHere && <span className="target-dot" />}
              {piece && <span className={clsx("piece", piece === piece.toUpperCase() ? "white" : "black")}>{pieceMap[piece] ?? piece}</span>}
            </button>
          );
        })}
      </div>
    </div>
  );
}
