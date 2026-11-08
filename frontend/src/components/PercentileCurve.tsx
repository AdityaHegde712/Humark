import React from 'react';
import { Sparkles, Brain, Award, ShieldAlert } from 'lucide-react';
import { PercentileBenchmarkResponse } from '../api/types';

export interface PercentileCurveProps {
  percentileBenchmark: PercentileBenchmarkResponse;
  className?: string;
}

export const PercentileCurve: React.FC<PercentileCurveProps> = ({
  percentileBenchmark,
  className = '',
}) => {
  const {
    percentile,
    is_top_2_percent,
    beats_frontier_ai,
    tier_label,
    curve_points,
    user_point,
    frontier_point,
  } = percentileBenchmark;

  // SVG coordinate transformation system
  // Data range: x in [0.20, 0.85], y in [0.0, 1.0]
  const svgWidth = 600;
  const svgHeight = 220;
  const paddingX = 40;
  const paddingTop = 30;
  const paddingBottom = 40;

  const plotWidth = svgWidth - 2 * paddingX;
  const plotHeight = svgHeight - paddingTop - paddingBottom;

  const minX = 0.20;
  const maxX = 0.85;

  const toSvgX = (x: number) => {
    const clampedX = Math.max(minX, Math.min(maxX, x));
    return paddingX + ((clampedX - minX) / (maxX - minX)) * plotWidth;
  };

  const toSvgY = (y: number) => {
    // Invert y: y=1.0 is at the top of plotHeight, y=0.0 is at the baseline
    return paddingTop + plotHeight * (1 - y);
  };

  // Build SVG path string for the curve
  const pathData = curve_points.reduce((acc, [x, y], idx) => {
    const sx = toSvgX(x).toFixed(1);
    const sy = toSvgY(y).toFixed(1);
    return idx === 0 ? `M ${sx} ${sy}` : `${acc} L ${sx} ${sy}`;
  }, '');

  // Fill area under curve
  const baselineY = toSvgY(0).toFixed(1);
  const startX = toSvgX(curve_points[0][0]).toFixed(1);
  const endX = toSvgX(curve_points[curve_points.length - 1][0]).toFixed(1);
  const areaData = `${pathData} L ${endX} ${baselineY} L ${startX} ${baselineY} Z`;

  // Key marker coordinates
  const chanceX = toSvgX(0.50);
  const medianX = toSvgX(0.528);
  const frontierX = toSvgX(frontier_point[0]);
  const frontierY = toSvgY(frontier_point[1]);
  const userX = toSvgX(user_point[0]);
  const userY = toSvgY(user_point[1]);

  return (
    <div
      className={`bg-zinc-900 border border-zinc-800 rounded-xl p-5 shadow-2xl relative overflow-hidden ${className}`}
    >
      {/* Dynamic Header Banner */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 mb-4 pb-4 border-b border-zinc-800/80">
        <div>
          <div className="flex items-center gap-2">
            {beats_frontier_ai ? (
              <Sparkles className="w-5 h-5 text-amber-400 animate-pulse" />
            ) : is_top_2_percent ? (
              <Award className="w-5 h-5 text-emerald-400" />
            ) : (
              <Brain className="w-5 h-5 text-purple-400" />
            )}
            <h3 className="text-sm font-semibold tracking-wide uppercase text-zinc-300">
              {beats_frontier_ai || is_top_2_percent
                ? 'Top 2% Human Edge'
                : 'Empirical Human Benchmark Standing'}
            </h3>
          </div>
          <p className="text-xs text-zinc-400 mt-0.5">
            Ranked against WONO empirical study of 7,030 human evaluators ($\mu=52.8\%$, $\sigma=9.4\%$)
          </p>
        </div>

        {/* Tier badge */}
        <div
          className={`inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold self-start sm:self-auto border ${
            beats_frontier_ai
              ? 'bg-amber-950/40 text-amber-300 border-amber-500/50 shadow-[0_0_15px_rgba(245,158,11,0.2)]'
              : is_top_2_percent
              ? 'bg-emerald-950/40 text-emerald-300 border-emerald-500/50 shadow-[0_0_15px_rgba(16,185,129,0.2)]'
              : 'bg-zinc-800 text-zinc-300 border-zinc-700'
          }`}
        >
          {beats_frontier_ai ? (
            <Sparkles className="w-3.5 h-3.5 text-amber-400" />
          ) : is_top_2_percent ? (
            <Award className="w-3.5 h-3.5 text-emerald-400" />
          ) : (
            <Brain className="w-3.5 h-3.5 text-zinc-400" />
          )}
          <span>{tier_label}</span>
        </div>
      </div>

      {/* Primary Highlight Message */}
      <div
        className={`p-3 rounded-lg text-xs leading-relaxed mb-4 flex items-start gap-2.5 border ${
          beats_frontier_ai
            ? 'bg-amber-950/20 text-amber-200 border-amber-800/40'
            : is_top_2_percent
            ? 'bg-emerald-950/20 text-emerald-200 border-emerald-800/40'
            : 'bg-zinc-950/40 text-zinc-300 border-zinc-800/60'
        }`}
      >
        {beats_frontier_ai ? (
          <Sparkles className="w-4 h-4 text-amber-400 shrink-0 mt-0.5" />
        ) : is_top_2_percent ? (
          <Award className="w-4 h-4 text-emerald-400 shrink-0 mt-0.5" />
        ) : (
          <ShieldAlert className="w-4 h-4 text-zinc-400 shrink-0 mt-0.5" />
        )}
        <div>
          {beats_frontier_ai ? (
            <span>
              <strong>TOP 2% HUMAN EVALUATOR:</strong> You outperform{' '}
              <strong className="text-amber-300">{percentile}%</strong> of the human benchmark and
              beat frontier multimodal AI baseline (75.0%).
            </span>
          ) : is_top_2_percent ? (
            <span>
              <strong>TOP 2% HUMAN TIER:</strong> You outperform{' '}
              <strong className="text-emerald-300">{percentile}%</strong> of the human benchmark,
              operating within the elite human cluster that rivals frontier AI.
            </span>
          ) : (
            <span>
              <strong>HUMAN BENCHMARK STANDING:</strong> You outperformed{' '}
              <strong className="text-purple-300">{percentile}%</strong> of 7,030 human participants.
              Frontier multimodal AI baseline operates at <strong>75.0%</strong> (98.9th percentile).
            </span>
          )}
        </div>
      </div>

      {/* Bell Curve SVG Visualization */}
      <div className="w-full relative select-none">
        <svg
          viewBox={`0 0 ${svgWidth} ${svgHeight}`}
          className="w-full h-auto overflow-visible"
        >
          <defs>
            {/* Area gradient under curve */}
            <linearGradient id="bellGradient" x1="0%" y1="0%" x2="0%" y2="100%">
              <stop offset="0%" stopColor="#8b5cf6" stopOpacity="0.35" />
              <stop offset="70%" stopColor="#6366f1" stopOpacity="0.10" />
              <stop offset="100%" stopColor="#18181b" stopOpacity="0.0" />
            </linearGradient>

            {/* Top 2% zone glow gradient */}
            <linearGradient id="topEdgeGradient" x1="0%" y1="0%" x2="100%" y2="0%">
              <stop offset="0%" stopColor="#8b5cf6" stopOpacity="0.2" />
              <stop offset="100%" stopColor="#10b981" stopOpacity="0.4" />
            </linearGradient>

            {/* User pin filter glow */}
            <filter id="userGlow" x="-20%" y="-20%" width="140%" height="140%">
              <feGaussianBlur stdDeviation="3" result="blur" />
              <feComposite in="SourceGraphic" in2="blur" operator="over" />
            </filter>
          </defs>

          {/* Baseline horizontal axis */}
          <line
            x1={paddingX}
            y1={toSvgY(0)}
            x2={svgWidth - paddingX}
            y2={toSvgY(0)}
            stroke="#3f3f46"
            strokeWidth="1.5"
          />

          {/* Filled Bell Curve */}
          <path d={areaData} fill="url(#bellGradient)" />

          {/* Spline Bell Curve Line */}
          <path
            d={pathData}
            fill="none"
            stroke="#a1a1aa"
            strokeWidth="2"
            strokeLinecap="round"
            strokeLinejoin="round"
          />

          {/* Guide Line: 50% Random Chance */}
          <line
            x1={chanceX}
            y1={toSvgY(0)}
            x2={chanceX}
            y2={paddingTop + 20}
            stroke="#71717a"
            strokeWidth="1"
            strokeDasharray="3 3"
          />
          <text
            x={chanceX}
            y={toSvgY(0) + 16}
            fill="#71717a"
            fontSize="10"
            textAnchor="middle"
            fontFamily="monospace"
          >
            50% Floor
          </text>

          {/* Guide Line: 52.8% Human Median */}
          <line
            x1={medianX}
            y1={toSvgY(0)}
            x2={medianX}
            y2={paddingTop}
            stroke="#94a3b8"
            strokeWidth="1.5"
            strokeDasharray="4 4"
          />
          <text
            x={medianX}
            y={paddingTop - 8}
            fill="#94a3b8"
            fontSize="10"
            textAnchor="middle"
            fontWeight="500"
          >
            Median (52.8%)
          </text>

          {/* Guide Line: 75.0% Frontier AI Baseline */}
          <line
            x1={frontierX}
            y1={toSvgY(0)}
            x2={frontierX}
            y2={paddingTop - 12}
            stroke="#a855f7"
            strokeWidth="1.5"
            strokeDasharray="3 3"
          />
          {/* Frontier AI Dot */}
          <circle
            cx={frontierX}
            cy={frontierY}
            r="4.5"
            fill="#a855f7"
            stroke="#18181b"
            strokeWidth="2"
          />
          <text
            x={frontierX}
            y={paddingTop - 16}
            fill="#c084fc"
            fontSize="10"
            textAnchor="middle"
            fontWeight="600"
          >
            Frontier AI (75.0%)
          </text>
          <text
            x={frontierX}
            y={toSvgY(0) + 16}
            fill="#a855f7"
            fontSize="9"
            textAnchor="middle"
          >
            98.9th %ile
          </text>

          {/* User Marker Pin */}
          <line
            x1={userX}
            y1={toSvgY(0)}
            x2={userX}
            y2={Math.min(userY, paddingTop + 20)}
            stroke={beats_frontier_ai ? '#fbbf24' : is_top_2_percent ? '#34d399' : '#38bdf8'}
            strokeWidth="2"
          />
          <circle
            cx={userX}
            cy={userY}
            r="6"
            fill={beats_frontier_ai ? '#fbbf24' : is_top_2_percent ? '#34d399' : '#38bdf8'}
            stroke="#09090b"
            strokeWidth="2"
            filter="url(#userGlow)"
          />
          {/* User Score Label Tooltip Tag */}
          <g transform={`translate(${userX}, ${Math.min(userY - 14, paddingTop + 10)})`}>
            <rect
              x="-48"
              y="-18"
              width="96"
              height="20"
              rx="4"
              fill="#18181b"
              stroke={beats_frontier_ai ? '#fbbf24' : is_top_2_percent ? '#34d399' : '#38bdf8'}
              strokeWidth="1"
            />
            <text
              x="0"
              y="-4"
              fill={beats_frontier_ai ? '#fef08a' : is_top_2_percent ? '#a7f3d0' : '#bae6fd'}
              fontSize="10"
              fontWeight="bold"
              textAnchor="middle"
            >
              You: {(user_point[0] * 100).toFixed(1)}% ({percentile}%)
            </text>
          </g>
        </svg>
      </div>

      {/* Footer Legend */}
      <div className="flex flex-wrap items-center justify-between gap-2 mt-2 pt-3 border-t border-zinc-800 text-[11px] text-zinc-400">
        <div className="flex items-center gap-4">
          <div className="flex items-center gap-1.5">
            <span className="w-2.5 h-2.5 rounded-full bg-slate-400 inline-block" />
            <span>Human Median: 52.8%</span>
          </div>
          <div className="flex items-center gap-1.5">
            <span className="w-2.5 h-2.5 rounded-full bg-purple-500 inline-block" />
            <span>Frontier AI: 75.0% (Beats 98% humans)</span>
          </div>
          <div className="flex items-center gap-1.5">
            <span
              className={`w-2.5 h-2.5 rounded-full inline-block ${
                beats_frontier_ai
                  ? 'bg-amber-400'
                  : is_top_2_percent
                  ? 'bg-emerald-400'
                  : 'bg-sky-400'
              }`}
            />
            <span>Your Standing</span>
          </div>
        </div>
        <div className="text-zinc-400 text-xs font-mono">
          z-score: {percentileBenchmark.z_score > 0 ? `+${percentileBenchmark.z_score.toFixed(2)}` : percentileBenchmark.z_score.toFixed(2)}
        </div>
      </div>
    </div>
  );
};

export default PercentileCurve;
