import React from 'react';
import { RotateCcw, Flame, Trophy, BarChart3, LayoutGrid } from 'lucide-react';

export interface HeaderProps {
  currentRound: number;
  attemptIndex: number;
  totalRoundItems: number;
  totalCorrect: number;
  totalAttempts: number;
  onResetSession: () => void;
  isResetting?: boolean;
  currentView?: 'challenge' | 'scorecard';
  onToggleView?: (view: 'challenge' | 'scorecard') => void;
}

export const Header: React.FC<HeaderProps> = ({
  currentRound = 1,
  attemptIndex = 1,
  totalRoundItems = 10,
  totalCorrect = 0,
  totalAttempts = 0,
  onResetSession,
  isResetting = false,
  currentView = 'challenge',
  onToggleView,
}) => {
  // Round label resolver
  const getRoundLabel = (round: number): { title: string; subtitle: string; color: string } => {
    switch (round) {
      case 2:
        return {
          title: 'Round 2 of 3',
          subtitle: 'Verification',
          color: 'text-blue-400 border-blue-500/30 bg-blue-500/10',
        };
      case 3:
        return {
          title: 'Round 3 of 3',
          subtitle: 'Confirmation',
          color: 'text-purple-400 border-purple-500/30 bg-purple-500/10',
        };
      case 1:
      default:
        return {
          title: 'Round 1 of 3',
          subtitle: 'Calibration',
          color: 'text-amber-400 border-amber-500/30 bg-amber-500/10',
        };
    }
  };

  const roundInfo = getRoundLabel(currentRound);

  // Score calculation
  const accuracyPct =
    totalAttempts > 0 ? ((totalCorrect / totalAttempts) * 100).toFixed(1) : '0.0';

  // Progress percentage (bounded 0 - 100%)
  const clampedIndex = Math.min(Math.max(attemptIndex, 0), totalRoundItems);
  const progressPercent = totalRoundItems > 0 ? (clampedIndex / totalRoundItems) * 100 : 0;

  return (
    <header className="border-b border-[#27272a] bg-[#121212]/95 backdrop-blur sticky top-0 z-50 px-4 sm:px-6 py-3.5">
      <div className="max-w-7xl mx-auto flex flex-col md:flex-row md:items-center md:justify-between gap-3">
        {/* Logo and Tagline */}
        <div className="flex items-center space-x-3">
          <div className="w-9 h-9 rounded-lg bg-gradient-to-br from-amber-500 via-rose-500 to-red-600 flex items-center justify-center font-black text-black text-base shadow-sm ring-1 ring-white/10">
            H
          </div>
          <div>
            <div className="flex items-center space-x-2">
              <span className="font-extrabold text-lg tracking-tight text-[#f4f4f5]">HUMARK</span>
              <span className="text-[10px] font-mono tracking-wide uppercase px-1.5 py-0.5 rounded border border-[#27272a] bg-[#18181b] text-[#a1a1aa]">
                v0.1.0
              </span>
            </div>
            <p className="text-xs text-[#a1a1aa]">Human vs AI Benchmark Harness</p>
          </div>
        </div>

        {/* Center / Right Metadata Telemetry */}
        <div className="flex flex-wrap items-center gap-2 sm:gap-3">
          {/* Round Pill Badge */}
          <div
            className={`flex items-center space-x-1.5 text-xs font-medium px-3 py-1.5 rounded-full border ${roundInfo.color}`}
          >
            <Flame className="w-3.5 h-3.5" />
            <span className="font-semibold">{roundInfo.title}</span>
            <span className="opacity-80 font-normal">({roundInfo.subtitle})</span>
          </div>

          {/* Progress Tracker Pill & Visual Progress Bar */}
          <div className="flex items-center space-x-2 text-xs border border-[#27272a] bg-[#18181b] px-3 py-1.5 rounded-md min-w-[140px]">
            <div className="flex-1">
              <div className="flex items-center justify-between text-[11px] mb-1">
                <span className="text-[#a1a1aa]">Progress</span>
                <span className="font-mono font-medium text-[#f4f4f5]">
                  Item {clampedIndex} / {totalRoundItems}
                </span>
              </div>
              <div className="w-full bg-[#27272a] h-1.5 rounded-full overflow-hidden">
                <div
                  className="bg-amber-400 h-full rounded-full transition-all duration-300 ease-out"
                  style={{ width: `${progressPercent}%` }}
                />
              </div>
            </div>
          </div>

          {/* Score Counter */}
          <div className="flex items-center space-x-2 text-xs border border-[#27272a] bg-[#18181b] px-3 py-1.5 rounded-md">
            <Trophy className="w-3.5 h-3.5 text-amber-400" />
            <span className="text-[#a1a1aa]">Score:</span>
            <span className="font-mono font-semibold text-[#f4f4f5]">
              {totalCorrect} / {totalAttempts}
            </span>
            <span className="text-[11px] font-mono text-emerald-400 font-medium">
              ({accuracyPct}%)
            </span>
          </div>

          {/* View Toggle (Challenge vs Scorecard) */}
          {onToggleView && totalAttempts > 0 && (
            <div className="flex items-center rounded-md border border-[#27272a] bg-[#18181b] p-0.5">
              {!(currentRound === 3 && attemptIndex >= totalRoundItems) && (
                <button
                  type="button"
                  onClick={() => onToggleView('challenge')}
                  className={`inline-flex items-center space-x-1.5 text-xs px-2.5 py-1 rounded transition-colors ${
                    currentView === 'challenge'
                      ? 'bg-neutral-800 text-white font-medium'
                      : 'text-[#a1a1aa] hover:text-[#f4f4f5]'
                  }`}
                >
                  <LayoutGrid className="w-3.5 h-3.5" />
                  <span className="hidden sm:inline">Challenge</span>
                </button>
              )}
              <button
                type="button"
                onClick={() => onToggleView('scorecard')}
                className={`inline-flex items-center space-x-1.5 text-xs px-2.5 py-1 rounded transition-colors ${
                  currentView === 'scorecard'
                    ? 'bg-neutral-800 text-white font-medium'
                    : 'text-[#a1a1aa] hover:text-[#f4f4f5]'
                }`}
              >
                <BarChart3 className="w-3.5 h-3.5" />
                <span>Scorecard</span>
              </button>
            </div>
          )}

          {/* Reset / New Run Button */}
          <button
            type="button"
            onClick={onResetSession}
            disabled={isResetting}
            title="Reset session and start a new benchmark run"
            className="inline-flex items-center space-x-1.5 text-xs border border-[#27272a] bg-[#18181b] hover:bg-[#222226] hover:border-neutral-700 text-[#a1a1aa] hover:text-[#f4f4f5] px-3 py-1.5 rounded-md transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
          >
            <RotateCcw className={`w-3.5 h-3.5 ${isResetting ? 'animate-spin' : ''}`} />
            <span>New Run</span>
          </button>
        </div>
      </div>
    </header>
  );
};

export default Header;
