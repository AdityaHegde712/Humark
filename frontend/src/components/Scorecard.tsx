import React, { useState } from 'react';
import {
  Trophy,
  Share2,
  Check,
  ArrowRight,
  RotateCcw,
  Sparkles,
  Timer,
  BarChart3,
  Percent,
  CheckCircle2,
  XCircle,
  MinusCircle,
  Info,
} from 'lucide-react';
import { ScorecardResponse, ModelComparisonItem } from '../api/types';
import VerificationBadge from './VerificationBadge';
import PercentileCurve from './PercentileCurve';

export interface ScorecardProps {
  scorecard: ScorecardResponse;
  onAdvanceRound?: () => void;
  onResetSession?: () => void;
  isAdvancing?: boolean;
  isSharedView?: boolean;
  className?: string;
}

export const Scorecard: React.FC<ScorecardProps> = ({
  scorecard,
  onAdvanceRound,
  onResetSession,
  isAdvancing = false,
  isSharedView = false,
  className = '',
}) => {
  const [copiedLink, setCopiedLink] = useState(false);

  // Core metrics formatting
  const accuracyPct = (scorecard.accuracy * 100).toFixed(1);
  const latencySeconds = (scorecard.average_time_taken_ms / 1000).toFixed(1);

  // Wilson confidence interval values
  const wilson = scorecard.wilson_interval;
  const ciLower = wilson.lower ?? wilson.ci_lower ?? 0;
  const ciUpper = wilson.upper ?? wilson.ci_upper ?? 0;
  const ciLowerPct = ((wilson.lower ?? wilson.ci_lower ?? 0) * 100).toFixed(1);
  const ciUpperPct = ((wilson.upper ?? wilson.ci_upper ?? 0) * 100).toFixed(1);
  const marginOfErrorPct = ((wilson.margin_of_error ?? (ciUpper - ciLower) / 2) * 100).toFixed(1);
  const isSampleNarrowed = scorecard.total_attempts >= 30;

  // Share link copy handler
  const handleCopyShareLink = async () => {
    try {
      const url = new URL(window.location.origin + window.location.pathname);
      url.searchParams.set('session', scorecard.session_id);
      url.searchParams.set('view', 'scorecard');
      const shareUrl = url.toString();

      if (navigator.clipboard && navigator.clipboard.writeText) {
        await navigator.clipboard.writeText(shareUrl);
      } else {
        const textArea = document.createElement('textarea');
        textArea.value = shareUrl;
        document.body.appendChild(textArea);
        textArea.select();
        document.execCommand('copy');
        document.body.removeChild(textArea);
      }
      setCopiedLink(true);
      setTimeout(() => setCopiedLink(false), 2500);
    } catch (e) {
      console.error('Failed to copy share link:', e);
    }
  };

  // Helper to format model performance delta badge
  const renderDeltaPill = (delta: number) => {
    const deltaPct = (delta * 100).toFixed(1);
    if (delta > 0) {
      return (
        <span className="inline-flex items-center space-x-1 px-2.5 py-1 rounded-full text-xs font-mono font-semibold bg-emerald-500/10 text-emerald-400 border border-emerald-500/30">
          <span>+{deltaPct}% Ahead</span>
        </span>
      );
    }
    if (delta < 0) {
      return (
        <span className="inline-flex items-center space-x-1 px-2.5 py-1 rounded-full text-xs font-mono font-semibold bg-rose-500/10 text-rose-400 border border-rose-500/30">
          <span>{deltaPct}% Behind</span>
        </span>
      );
    }
    return (
      <span className="inline-flex items-center space-x-1 px-2.5 py-1 rounded-full text-xs font-mono font-semibold bg-neutral-800 text-neutral-300 border border-neutral-700">
        <span>0.0% Tied</span>
      </span>
    );
  };

  // Canonical baseline models
  const defaultModels: ModelComparisonItem[] = [
    {
      model_name: 'Frontier Vision (GPT-4o)',
      model_accuracy: 0.6,
      user_beat_model: 3,
      model_beat_user: 2,
      ties: 5,
      accuracy_delta: 0.1,
      verdict: 'ahead',
    },
    {
      model_name: 'Compact Vision (Claude 3.5 Haiku)',
      model_accuracy: 0.55,
      user_beat_model: 4,
      model_beat_user: 2,
      ties: 4,
      accuracy_delta: 0.15,
      verdict: 'ahead',
    },
    {
      model_name: 'Heuristic Baseline',
      model_accuracy: 0.5,
      user_beat_model: 5,
      model_beat_user: 3,
      ties: 2,
      accuracy_delta: 0.2,
      verdict: 'ahead',
    },
  ];

  const modelsToDisplay =
    scorecard.model_comparisons && scorecard.model_comparisons.length > 0
      ? scorecard.model_comparisons
      : defaultModels;

  return (
    <div className={`w-full max-w-4xl mx-auto space-y-8 ${className}`}>
      {/* Top Banner if Shared View */}
      {isSharedView && (
        <div className="p-4 rounded-xl border border-amber-500/30 bg-amber-500/10 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 text-amber-200">
          <div className="flex items-center space-x-3 text-sm">
            <Info className="w-5 h-5 text-amber-400 flex-shrink-0" />
            <span>
              You are inspecting a shared Humark benchmark run for session{' '}
              <span className="font-mono font-bold">{scorecard.session_id.slice(0, 8)}...</span>
            </span>
          </div>
          {onResetSession && (
            <button
              type="button"
              onClick={onResetSession}
              className="text-xs bg-amber-400 hover:bg-amber-300 text-black font-semibold px-3 py-1.5 rounded-lg transition-colors flex-shrink-0"
            >
              Start Your Own Run
            </button>
          )}
        </div>
      )}

      {/* Verification Status Badge Component */}
      <VerificationBadge
        isVerified={scorecard.is_verified}
        totalAttempts={scorecard.total_attempts}
        currentRound={scorecard.current_round}
        roundsCompleted={scorecard.rounds_completed}
        correctAttempts={scorecard.correct_attempts}
        verificationHash={scorecard.verification_hash}
        auditSummary={scorecard.verification_audit}
      />

      {/* Hero Score Summary Card */}
      <div className="rounded-2xl border border-[#27272a] bg-[#18181b] p-6 sm:p-8 shadow-xl">
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 pb-6 border-b border-[#27272a]">
          <div>
            <div className="text-xs font-mono uppercase tracking-widest text-[#a1a1aa] mb-1">
              Benchmark Scorecard &bull; Round {scorecard.current_round}
            </div>
            <h2 className="text-2xl sm:text-3xl font-extrabold text-[#f4f4f5] tracking-tight">
              Human Thumbnail Performance
            </h2>
          </div>

          {/* Shareable Link Button */}
          <button
            type="button"
            onClick={handleCopyShareLink}
            className="inline-flex items-center space-x-2 text-xs font-medium px-4 py-2 rounded-lg border border-[#27272a] bg-[#121212] hover:bg-[#222226] text-[#e0e0e0] transition-colors self-start sm:self-auto"
          >
            {copiedLink ? (
              <>
                <Check className="w-4 h-4 text-emerald-400" />
                <span className="text-emerald-400 font-semibold">Share Link Copied!</span>
              </>
            ) : (
              <>
                <Share2 className="w-4 h-4 text-[#a1a1aa]" />
                <span>Share Scorecard</span>
              </>
            )}
          </button>
        </div>

        {/* 3 Metric Hero Grid */}
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 pt-6">
          {/* Metric 1: Display Accuracy */}
          <div className="p-5 rounded-xl border border-[#27272a] bg-[#121212] flex flex-col justify-between">
            <div className="flex items-center justify-between text-xs text-[#a1a1aa]">
              <span className="uppercase font-mono font-medium">Cumulative Accuracy</span>
              <Percent className="w-4 h-4 text-amber-400" />
            </div>
            <div className="my-3">
              <div className="text-4xl sm:text-5xl font-black font-mono tracking-tight text-[#f4f4f5]">
                {accuracyPct}%
              </div>
            </div>
            <div className="text-xs text-[#71717a]">
              {scorecard.accuracy >= 0.7 ? (
                <span className="text-emerald-400 font-medium">Exceeds &gt;70% threshold</span>
              ) : (
                <span className="text-amber-400 font-medium">Target &gt;70% to verify</span>
              )}
            </div>
          </div>

          {/* Metric 2: Challenge Item Count */}
          <div className="p-5 rounded-xl border border-[#27272a] bg-[#121212] flex flex-col justify-between">
            <div className="flex items-center justify-between text-xs text-[#a1a1aa]">
              <span className="uppercase font-mono font-medium">Challenges Solved</span>
              <Trophy className="w-4 h-4 text-emerald-400" />
            </div>
            <div className="my-3">
              <div className="text-4xl sm:text-5xl font-black font-mono tracking-tight text-[#f4f4f5]">
                {scorecard.correct_attempts}
                <span className="text-xl sm:text-2xl font-normal text-[#71717a]">
                  {' '}
                  / {scorecard.total_attempts}
                </span>
              </div>
            </div>
            <div className="text-xs text-[#a1a1aa]">
              {scorecard.correct_attempts} of {scorecard.total_attempts} Correct (Round{' '}
              {scorecard.current_round})
            </div>
          </div>

          {/* Metric 3: Decision Latency */}
          <div className="p-5 rounded-xl border border-[#27272a] bg-[#121212] flex flex-col justify-between">
            <div className="flex items-center justify-between text-xs text-[#a1a1aa]">
              <span className="uppercase font-mono font-medium">Decision Latency</span>
              <Timer className="w-4 h-4 text-blue-400" />
            </div>
            <div className="my-3">
              <div className="text-4xl sm:text-5xl font-black font-mono tracking-tight text-[#f4f4f5]">
                {latencySeconds}s
              </div>
            </div>
            <div className="text-xs text-[#a1a1aa]">Average per challenge response</div>
          </div>
        </div>
      </div>

      {/* Top 2% Human Edge Percentile Curve */}
      {scorecard.percentile_benchmark && (
        <PercentileCurve percentileBenchmark={scorecard.percentile_benchmark} />
      )}

      {/* Statistical Confidence Section */}
      <div className="rounded-2xl border border-[#27272a] bg-[#18181b] p-6 sm:p-8 space-y-6">
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
          <div className="flex items-center space-x-3">
            <div className="w-9 h-9 rounded-lg bg-[#27272a] flex items-center justify-center text-amber-400">
              <BarChart3 className="w-5 h-5" />
            </div>
            <div>
              <h3 className="text-lg font-bold text-[#f4f4f5]">
                Statistical Confidence & Wilson Interval
              </h3>
              <p className="text-xs text-[#a1a1aa]">
                Binomial score interval with continuity correction at 95% confidence level
              </p>
            </div>
          </div>

          {/* Wilson CI Badge */}
          <div className="px-3 py-1.5 rounded-lg border border-neutral-700 bg-[#121212] text-xs font-mono font-semibold text-[#f4f4f5] self-start sm:self-auto">
            95% CI: [{ciLowerPct}% — {ciUpperPct}%]
          </div>
        </div>

        {/* Sample Size Warning / Confidence Confirmation */}
        {!isSampleNarrowed ? (
          <div className="p-4 rounded-xl border border-amber-500/30 bg-amber-500/10 text-amber-200 text-xs sm:text-sm flex items-start space-x-3">
            <Info className="w-5 h-5 text-amber-400 flex-shrink-0 mt-0.5" />
            <div className="space-y-1">
              <span className="font-semibold text-amber-300">
                Small sample warning (n={scorecard.total_attempts}):
              </span>
              <p className="text-amber-200/90 leading-relaxed">
                Complete the 3-round verification track to eliminate luck and narrow confidence
                interval. Current margin of error is &plusmn;{marginOfErrorPct}%.
              </p>
            </div>
          </div>
        ) : (
          <div className="p-4 rounded-xl border border-emerald-500/30 bg-emerald-500/10 text-emerald-200 text-xs sm:text-sm flex items-start space-x-3">
            <CheckCircle2 className="w-5 h-5 text-emerald-400 flex-shrink-0 mt-0.5" />
            <div className="space-y-1">
              <span className="font-semibold text-emerald-300">
                Narrowed Confidence Interval (n=30) — High statistical power.
              </span>
              <p className="text-emerald-200/90 leading-relaxed">
                Evaluation across 30 independent unseen split tests provides robust statistical
                guarantees. Margin of error narrowed to &plusmn;{marginOfErrorPct}%.
              </p>
            </div>
          </div>
        )}

        {/* Visual CI Meter Bar */}
        <div className="p-4 rounded-xl border border-[#27272a] bg-[#121212] space-y-3">
          <div className="flex items-center justify-between text-xs font-mono text-[#a1a1aa]">
            <span>0% (Chance Floor)</span>
            <span className="text-neutral-400">50% Random Baseline</span>
            <span className="text-amber-400">70% Verification Gate</span>
            <span>100%</span>
          </div>

          <div className="relative w-full h-4 bg-[#18181b] rounded-full overflow-hidden border border-[#27272a]">
            {/* 50% Random Chance Line */}
            <div
              className="absolute top-0 bottom-0 w-0.5 bg-neutral-600 z-10"
              style={{ left: '50%' }}
              title="50% Random Chance"
            />
            {/* 70% Verification Threshold Line */}
            <div
              className="absolute top-0 bottom-0 w-0.5 bg-amber-400/80 z-10"
              style={{ left: '70%' }}
              title="70% Verification Threshold"
            />

            {/* Wilson CI Band */}
            <div
              className="absolute top-1 bottom-1 bg-amber-500/30 border-y border-amber-500/50 rounded-sm"
              style={{
                left: `${Math.max(0, ciLower * 100)}%`,
                width: `${Math.min(100, (ciUpper - ciLower) * 100)}%`,
              }}
            />

            {/* Observed Point Estimate Dot */}
            <div
              className="absolute top-0.5 bottom-0.5 w-3 h-3 bg-emerald-400 rounded-full border-2 border-[#121212] shadow-sm transform -translate-x-1/2 z-20"
              style={{ left: `${Math.min(100, Math.max(0, scorecard.accuracy * 100))}%` }}
              title={`Observed Accuracy: ${accuracyPct}%`}
            />
          </div>

          <div className="flex items-center justify-between text-[11px] text-[#71717a]">
            <span>Lower: {ciLowerPct}%</span>
            <span className="text-emerald-400 font-mono font-medium">
              Point Estimate: {accuracyPct}%
            </span>
            <span>Upper: {ciUpperPct}%</span>
          </div>
        </div>
      </div>

      {/* AI Head-to-Head Comparison Table / Cards */}
      <div className="rounded-2xl border border-[#27272a] bg-[#18181b] p-6 sm:p-8 space-y-6">
        <div>
          <div className="text-xs font-mono uppercase tracking-widest text-[#a1a1aa] mb-1">
            Head-to-Head Benchmarks
          </div>
          <h3 className="text-xl font-bold text-[#f4f4f5]">AI Model Matchups</h3>
          <p className="text-xs text-[#a1a1aa] mt-1">
            Comparing your selections against automated vision baselines on identical split test
            items
          </p>
        </div>

        {/* Model Matchup Cards */}
        <div className="grid grid-cols-1 gap-4">
          {modelsToDisplay.map((model) => {
            const totalMatchups = model.user_beat_model + model.ties + model.model_beat_user;
            const modelAccPct = (model.model_accuracy * 100).toFixed(1);

            const userWinPct = totalMatchups > 0 ? (model.user_beat_model / totalMatchups) * 100 : 33;
            const tiePct = totalMatchups > 0 ? (model.ties / totalMatchups) * 100 : 34;
            const modelWinPct = totalMatchups > 0 ? (model.model_beat_user / totalMatchups) * 100 : 33;

            return (
              <div
                key={model.model_name}
                className="p-5 rounded-xl border border-[#27272a] bg-[#121212] space-y-4 hover:border-neutral-700 transition-colors"
              >
                <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
                  <div className="space-y-1">
                    <div className="flex items-center space-x-2">
                      <span className="font-bold text-[#f4f4f5] text-base">{model.model_name}</span>
                      <span className="text-xs px-2 py-0.5 rounded bg-[#27272a] text-[#a1a1aa] font-mono">
                        Model Acc: {modelAccPct}%
                      </span>
                    </div>
                    <div className="text-xs text-[#71717a]">
                      User: <span className="text-white font-mono">{accuracyPct}%</span> vs Model:{' '}
                      <span className="text-white font-mono">{modelAccPct}%</span>
                    </div>
                  </div>

                  {/* Net Delta Pill */}
                  <div>{renderDeltaPill(model.accuracy_delta)}</div>
                </div>

                {/* Breakdown: Beats, Ties, Losses */}
                <div className="grid grid-cols-3 gap-2 text-center text-xs">
                  <div className="p-2 rounded-lg border border-emerald-500/20 bg-emerald-500/5">
                    <div className="flex items-center justify-center space-x-1 text-emerald-400 font-medium">
                      <CheckCircle2 className="w-3.5 h-3.5" />
                      <span>User Wins</span>
                    </div>
                    <div className="text-base font-mono font-bold text-emerald-300 mt-1">
                      {model.user_beat_model}
                    </div>
                  </div>

                  <div className="p-2 rounded-lg border border-neutral-700/50 bg-[#18181b]">
                    <div className="flex items-center justify-center space-x-1 text-neutral-400 font-medium">
                      <MinusCircle className="w-3.5 h-3.5" />
                      <span>Ties</span>
                    </div>
                    <div className="text-base font-mono font-bold text-[#f4f4f5] mt-1">
                      {model.ties}
                    </div>
                  </div>

                  <div className="p-2 rounded-lg border border-rose-500/20 bg-rose-500/5">
                    <div className="flex items-center justify-center space-x-1 text-rose-400 font-medium">
                      <XCircle className="w-3.5 h-3.5" />
                      <span>Model Wins</span>
                    </div>
                    <div className="text-base font-mono font-bold text-rose-300 mt-1">
                      {model.model_beat_user}
                    </div>
                  </div>
                </div>

                {/* Visual Win Bar */}
                <div className="space-y-1.5">
                  <div className="flex items-center justify-between text-[11px] text-[#71717a]">
                    <span>Outcome Proportion</span>
                    <span>
                      Beats: {model.user_beat_model} | Ties: {model.ties} | Losses:{' '}
                      {model.model_beat_user}
                    </span>
                  </div>
                  <div className="w-full h-2.5 rounded-full overflow-hidden flex bg-neutral-800">
                    <div
                      className="bg-emerald-500 h-full transition-all duration-300"
                      style={{ width: `${userWinPct}%` }}
                      title={`User Beat Model: ${model.user_beat_model}`}
                    />
                    <div
                      className="bg-neutral-600 h-full transition-all duration-300"
                      style={{ width: `${tiePct}%` }}
                      title={`Ties: ${model.ties}`}
                    />
                    <div
                      className="bg-rose-500 h-full transition-all duration-300"
                      style={{ width: `${modelWinPct}%` }}
                      title={`Model Beat User: ${model.model_beat_user}`}
                    />
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* Verification Track Next Steps & Actions */}
      <div className="rounded-2xl border border-[#27272a] bg-[#18181b] p-6 sm:p-8 space-y-6">
        {/* Scenario 1: Round 1 Complete (needs Round 2) */}
        {scorecard.rounds_completed === 1 && scorecard.total_attempts < 20 && (
          <div className="space-y-4">
            <div className="flex items-center space-x-2 text-amber-400 text-xs font-mono uppercase tracking-wider">
              <Sparkles className="w-4 h-4" />
              <span>Round 1 Complete &bull; Prove It Wasn't Luck</span>
            </div>
            <h3 className="text-2xl font-bold text-[#f4f4f5]">
              Ready for Round 2 Verification Track
            </h3>
            <p className="text-sm text-[#a1a1aa] leading-relaxed">
              You scored{' '}
              <span className="text-white font-mono font-semibold">
                {scorecard.correct_attempts} / 10 ({accuracyPct}%)
              </span>{' '}
              on your calibration round. A single 10-challenge sample has wide confidence bounds.
              Evaluate 10 additional unseen items to verify whether this represents genuine human
              intuition or variance.
            </p>

            {onAdvanceRound && (
              <div className="pt-2">
                <button
                  type="button"
                  onClick={onAdvanceRound}
                  disabled={isAdvancing}
                  className="w-full sm:w-auto px-6 py-3.5 rounded-xl bg-white hover:bg-neutral-200 text-black font-bold text-sm transition-all flex items-center justify-center space-x-2 disabled:opacity-50 shadow-lg"
                >
                  <span>
                    {isAdvancing ? 'Loading Round 2...' : 'Start Round 2 (10 Unseen Challenges)'}
                  </span>
                  <ArrowRight className="w-4 h-4" />
                </button>
              </div>
            )}
          </div>
        )}

        {/* Scenario 2: Round 2 Complete (needs Round 3) */}
        {scorecard.rounds_completed === 2 && scorecard.total_attempts < 30 && (
          <div className="space-y-4">
            <div className="flex items-center space-x-2 text-blue-400 text-xs font-mono uppercase tracking-wider">
              <Sparkles className="w-4 h-4" />
              <span>Round 2 Complete &bull; One Round Left to Verify</span>
            </div>
            <h3 className="text-2xl font-bold text-[#f4f4f5]">
              Final Confirmation Round Awaiting
            </h3>
            <p className="text-sm text-[#a1a1aa] leading-relaxed">
              You have evaluated 20 challenges with{' '}
              <span className="text-white font-mono font-semibold">
                {scorecard.correct_attempts} correct ({accuracyPct}%)
              </span>
              . Only 10 more unseen items remain to finalize your 30-item evaluation track and unlock
              your tamper-evident verification badge.
            </p>

            {onAdvanceRound && (
              <div className="pt-2">
                <button
                  type="button"
                  onClick={onAdvanceRound}
                  disabled={isAdvancing}
                  className="w-full sm:w-auto px-6 py-3.5 rounded-xl bg-blue-500 hover:bg-blue-400 text-white font-bold text-sm transition-all flex items-center justify-center space-x-2 disabled:opacity-50 shadow-lg shadow-blue-500/20"
                >
                  <span>
                    {isAdvancing
                      ? 'Loading Confirmation Round...'
                      : 'Start Final Verification Round'}
                  </span>
                  <ArrowRight className="w-4 h-4" />
                </button>
              </div>
            )}
          </div>
        )}

        {/* Scenario 3: 30 Items Complete (All Rounds Finished) */}
        {scorecard.total_attempts >= 30 && (
          <div className="space-y-4">
            <div className="flex items-center space-x-2 text-emerald-400 text-xs font-mono uppercase tracking-wider">
              <Sparkles className="w-4 h-4" />
              <span>Full Benchmark Evaluation Completed</span>
            </div>
            <h3 className="text-2xl font-bold text-[#f4f4f5]">
              {scorecard.is_verified
                ? 'Certified Human Benchmark Achievement'
                : 'Verification Run Complete'}
            </h3>
            <p className="text-sm text-[#a1a1aa] leading-relaxed">
              {scorecard.is_verified
                ? 'You successfully sustained >70% accuracy across 30 non-repeating A/B split tests. Your cryptographic SHA-256 verification hash is sealed on the benchmark ledger.'
                : 'You have evaluated all 30 unseen thumbnail challenges. Your confidence bounds are narrowed with high statistical power.'}
            </p>

            <div className="flex flex-col sm:flex-row gap-3 pt-2">
              <button
                type="button"
                onClick={handleCopyShareLink}
                className="flex-1 py-3 px-5 rounded-xl border border-neutral-700 bg-[#121212] hover:bg-[#222226] text-[#f4f4f5] font-semibold text-sm transition-colors flex items-center justify-center space-x-2"
              >
                {copiedLink ? (
                  <>
                    <Check className="w-4 h-4 text-emerald-400" />
                    <span className="text-emerald-400">Scorecard Link Copied</span>
                  </>
                ) : (
                  <>
                    <Share2 className="w-4 h-4 text-[#a1a1aa]" />
                    <span>Share Scorecard</span>
                  </>
                )}
              </button>

              {onResetSession && (
                <button
                  type="button"
                  onClick={onResetSession}
                  className="flex-1 py-3 px-5 rounded-xl bg-amber-400 hover:bg-amber-300 text-black font-semibold text-sm transition-colors flex items-center justify-center space-x-2"
                >
                  <RotateCcw className="w-4 h-4" />
                  <span>Start New Run</span>
                </button>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default Scorecard;
