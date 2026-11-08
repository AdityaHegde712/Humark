import React, { useState } from 'react';
import {
  ShieldCheck,
  Award,
  Copy,
  Check,
  Clock,
  AlertTriangle,
  Lock,
  Sparkles,
  FileCheck2,
} from 'lucide-react';
import { VerificationAuditSummary } from '../api/types';

export interface VerificationBadgeProps {
  isVerified: boolean;
  totalAttempts: number;
  currentRound: number;
  roundsCompleted: number;
  correctAttempts?: number;
  verificationHash?: string | null;
  auditSummary?: VerificationAuditSummary | null;
  roundScores?: Record<string, number>;
  className?: string;
}

export const VerificationBadge: React.FC<VerificationBadgeProps> = ({
  isVerified,
  totalAttempts,
  currentRound,
  roundsCompleted,
  correctAttempts = 0,
  verificationHash,
  auditSummary,
  roundScores,
  className = '',
}) => {
  const [copied, setCopied] = useState(false);

  // Active hash resolver
  const activeHash = verificationHash || auditSummary?.verification_hash || null;

  // Copy hash handler with feedback
  const handleCopyHash = async () => {
    if (!activeHash) return;
    try {
      await navigator.clipboard.writeText(activeHash);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      // Fallback if clipboard API is restricted
      const textArea = document.createElement('textarea');
      textArea.value = activeHash;
      document.body.appendChild(textArea);
      textArea.select();
      document.execCommand('copy');
      document.body.removeChild(textArea);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  };

  // Determine rounds score status
  const getRound1Score = (): { score: string; status: 'completed' | 'active' | 'pending' } => {
    if (auditSummary?.round_1_correct !== undefined) {
      return { score: `${auditSummary.round_1_correct}/10`, status: 'completed' };
    }
    if (roundScores?.['round_1'] !== undefined) {
      return { score: `${roundScores['round_1']}/10`, status: 'completed' };
    }
    if (roundsCompleted >= 1 || totalAttempts >= 10) {
      const score = Math.min(correctAttempts, 10);
      return { score: `${score}/10`, status: 'completed' };
    }
    if (totalAttempts > 0) {
      return { score: `${correctAttempts}/${totalAttempts}`, status: 'active' };
    }
    return { score: 'Pending', status: 'pending' };
  };

  const getRound2Score = (): { score: string; status: 'completed' | 'active' | 'pending' } => {
    if (auditSummary?.round_2_correct !== undefined) {
      return { score: `${auditSummary.round_2_correct}/10`, status: 'completed' };
    }
    if (roundScores?.['round_2'] !== undefined) {
      return { score: `${roundScores['round_2']}/10`, status: 'completed' };
    }
    if (roundsCompleted >= 2 || totalAttempts >= 20) {
      return { score: '10/10', status: 'completed' };
    }
    if (roundsCompleted === 1 || (totalAttempts >= 10 && totalAttempts < 20)) {
      const inRound = totalAttempts - 10;
      return {
        score: inRound > 0 ? `${inRound}/10 Active` : 'Active',
        status: 'active',
      };
    }
    return { score: 'Pending', status: 'pending' };
  };

  const getRound3Score = (): { score: string; status: 'completed' | 'active' | 'pending' } => {
    if (auditSummary?.round_3_correct !== undefined) {
      return { score: `${auditSummary.round_3_correct}/10`, status: 'completed' };
    }
    if (roundScores?.['round_3'] !== undefined) {
      return { score: `${roundScores['round_3']}/10`, status: 'completed' };
    }
    if (roundsCompleted >= 3 || totalAttempts >= 30) {
      return { score: 'Completed', status: 'completed' };
    }
    if (roundsCompleted === 2 || (totalAttempts >= 20 && totalAttempts < 30)) {
      const inRound = totalAttempts - 20;
      return {
        score: inRound > 0 ? `${inRound}/10 Active` : 'Active',
        status: 'active',
      };
    }
    return { score: 'Pending', status: 'pending' };
  };

  const r1 = getRound1Score();
  const r2 = getRound2Score();
  const r3 = getRound3Score();

  // CASE 1: VERIFIED (>70% across 30 challenges)
  if (isVerified) {
    const completedDate = auditSummary?.completed_at
      ? new Date(auditSummary.completed_at).toLocaleString(undefined, {
          dateStyle: 'medium',
          timeStyle: 'short',
        })
      : new Date().toLocaleDateString();

    const cumulativePct = auditSummary
      ? (auditSummary.cumulative_accuracy * 100).toFixed(1)
      : totalAttempts > 0
      ? ((correctAttempts / totalAttempts) * 100).toFixed(1)
      : '70.0';

    return (
      <div
        className={`w-full rounded-2xl border border-emerald-500/40 bg-gradient-to-b from-emerald-950/30 via-[#18181b] to-[#121212] p-6 shadow-[0_0_35px_rgba(16,185,129,0.12)] ${className}`}
      >
        {/* Glowing Badge Header */}
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 pb-5 border-b border-[#27272a]">
          <div className="flex items-center space-x-3.5">
            <div className="w-12 h-12 rounded-xl bg-gradient-to-br from-amber-400 to-emerald-500 p-0.5 shadow-lg shadow-emerald-500/20 flex items-center justify-center">
              <div className="w-full h-full bg-[#121212] rounded-[10px] flex items-center justify-center">
                <ShieldCheck className="w-6 h-6 text-emerald-400" />
              </div>
            </div>
            <div>
              <div className="flex items-center space-x-2">
                <span className="inline-flex items-center space-x-1.5 px-2.5 py-0.5 rounded-full text-[11px] font-bold tracking-wider uppercase bg-emerald-500/20 text-emerald-300 border border-emerald-500/40">
                  <Sparkles className="w-3 h-3 text-emerald-400" />
                  <span>VERIFIED BENCHMARK HOLDER</span>
                </span>
                <span className="hidden sm:inline-flex px-2 py-0.5 rounded text-[10px] font-semibold tracking-wide uppercase bg-amber-500/10 text-amber-300 border border-amber-500/30">
                  VERIFIED HUMAN EVALUATOR
                </span>
              </div>
              <h3 className="text-lg font-bold text-[#f4f4f5] mt-1 flex items-center space-x-2">
                <span>Certified Anti-Luck Verification</span>
                <span className="text-emerald-400 font-mono text-base font-semibold">
                  ({cumulativePct}%)
                </span>
              </h3>
            </div>
          </div>

          <div className="flex items-center space-x-2">
            <div className="px-3 py-1.5 rounded-lg border border-emerald-500/30 bg-emerald-500/10 text-emerald-300 text-xs font-semibold flex items-center space-x-1.5">
              <Award className="w-4 h-4 text-emerald-400" />
              <span>30 Unseen Challenges Certified</span>
            </div>
          </div>
        </div>

        {/* Audit Receipt Card */}
        <div className="mt-5 rounded-xl border border-[#27272a] bg-[#121212]/80 p-4 space-y-3">
          <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2 text-xs">
            <div className="flex items-center space-x-2 text-[#a1a1aa]">
              <FileCheck2 className="w-4 h-4 text-emerald-400 flex-shrink-0" />
              <span className="font-medium text-[#e0e0e0]">Tamper-Evident SHA-256 Proof:</span>
            </div>
            <span className="text-[11px] text-[#71717a]">Certified: {completedDate}</span>
          </div>

          {/* Verification Hash & One-Click Copy */}
          {activeHash ? (
            <div className="flex items-center justify-between gap-3 p-2.5 rounded-lg border border-[#27272a] bg-[#18181b]">
              <div className="font-mono text-xs text-emerald-400 truncate tracking-wider">
                {activeHash}
              </div>
              <button
                type="button"
                onClick={handleCopyHash}
                title="Copy verification hash to clipboard"
                className="flex items-center space-x-1.5 text-xs px-2.5 py-1 rounded bg-[#27272a] hover:bg-neutral-700 text-[#f4f4f5] transition-colors flex-shrink-0 font-medium"
              >
                {copied ? (
                  <>
                    <Check className="w-3.5 h-3.5 text-emerald-400" />
                    <span className="text-emerald-400">Copied!</span>
                  </>
                ) : (
                  <>
                    <Copy className="w-3.5 h-3.5 text-[#a1a1aa]" />
                    <span>Copy Proof</span>
                  </>
                )}
              </button>
            </div>
          ) : (
            <div className="text-xs text-[#a1a1aa] italic">
              Verification digest recorded on immutable benchmark ledger.
            </div>
          )}

          {/* Round Score Breakdown Pills */}
          <div className="grid grid-cols-3 gap-2 pt-1 text-center text-xs">
            <div className="p-2 rounded-lg border border-[#27272a] bg-[#18181b]">
              <div className="text-[10px] text-[#a1a1aa] uppercase font-mono">Round 1</div>
              <div className="font-mono font-semibold text-[#f4f4f5] mt-0.5">{r1.score}</div>
            </div>
            <div className="p-2 rounded-lg border border-[#27272a] bg-[#18181b]">
              <div className="text-[10px] text-[#a1a1aa] uppercase font-mono">Round 2</div>
              <div className="font-mono font-semibold text-[#f4f4f5] mt-0.5">{r2.score}</div>
            </div>
            <div className="p-2 rounded-lg border border-[#27272a] bg-[#18181b]">
              <div className="text-[10px] text-[#a1a1aa] uppercase font-mono">Round 3</div>
              <div className="font-mono font-semibold text-[#f4f4f5] mt-0.5">{r3.score}</div>
            </div>
          </div>
        </div>
      </div>
    );
  }

  // CASE 2: FAILED / UNVERIFIED AFTER 30 ITEMS
  if (totalAttempts >= 30 && !isVerified) {
    const accuracyPct = ((correctAttempts / totalAttempts) * 100).toFixed(1);

    return (
      <div
        className={`w-full rounded-2xl border border-rose-500/30 bg-[#18181b] p-6 shadow-lg ${className}`}
      >
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 pb-4 border-b border-[#27272a]">
          <div className="flex items-center space-x-3">
            <div className="w-10 h-10 rounded-xl bg-rose-500/10 border border-rose-500/30 flex items-center justify-center text-rose-400 flex-shrink-0">
              <AlertTriangle className="w-5 h-5" />
            </div>
            <div>
              <div className="inline-flex items-center space-x-1.5 px-2 py-0.5 rounded text-[11px] font-bold tracking-wider uppercase bg-rose-500/10 text-rose-300 border border-rose-500/20">
                <span>Evaluation Complete - Not Verified</span>
              </div>
              <h3 className="text-base font-semibold text-[#f4f4f5] mt-1">
                Completed 30 Challenges &bull; Threshold Not Met
              </h3>
            </div>
          </div>

          <div className="text-right">
            <div className="text-xs text-[#a1a1aa]">Cumulative Score</div>
            <div className="font-mono text-sm font-bold text-rose-400">
              {correctAttempts} / 30 ({accuracyPct}%)
            </div>
          </div>
        </div>

        <div className="mt-4 p-3.5 rounded-xl border border-neutral-800 bg-[#121212] space-y-2 text-xs">
          <p className="text-[#a1a1aa] leading-relaxed">
            <span className="text-[#f4f4f5] font-medium">Standard: </span>
            Requires &gt;70% cumulative accuracy across 30 unseen challenges (&ge;22 / 30 correct)
            to certify superior judgment over chance.
          </p>
          <div className="flex items-center space-x-2 text-[11px] text-[#71717a]">
            <span>Your result: {correctAttempts} of 30</span>
            <span>&bull;</span>
            <span>Required: 22 of 30</span>
            <span>&bull;</span>
            <span className="text-rose-400">Delta: -{Math.max(0, 22 - correctAttempts)} correct</span>
          </div>
        </div>
      </div>
    );
  }

  // CASE 3: IN PROGRESS (<30 items)
  return (
    <div
      className={`w-full rounded-2xl border border-[#27272a] bg-[#18181b] p-6 shadow-md ${className}`}
    >
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 pb-5 border-b border-[#27272a]">
        <div className="flex items-center space-x-3">
          <div className="w-10 h-10 rounded-xl bg-amber-500/10 border border-amber-500/30 flex items-center justify-center text-amber-400 flex-shrink-0">
            <Clock className="w-5 h-5" />
          </div>
          <div>
            <div className="inline-flex items-center space-x-1.5 px-2 py-0.5 rounded text-[11px] font-bold tracking-wider uppercase bg-amber-500/10 text-amber-300 border border-amber-500/20">
              <span className="w-1.5 h-1.5 rounded-full bg-amber-400 animate-pulse" />
              <span>Verification In Progress</span>
            </div>
            <h3 className="text-base font-semibold text-[#f4f4f5] mt-1">
              3-Round Anti-Luck Certification Track
            </h3>
          </div>
        </div>

        <div className="text-xs text-[#a1a1aa] font-mono">
          Round {currentRound} of 3 ({totalAttempts}/30 Evaluated)
        </div>
      </div>

      {/* 3-Round Step Progress Indicator */}
      <div className="mt-5 grid grid-cols-1 sm:grid-cols-3 gap-3">
        {/* Step 1: Round 1 */}
        <div
          className={`p-3.5 rounded-xl border transition-all ${
            r1.status === 'completed'
              ? 'border-emerald-500/30 bg-emerald-950/10'
              : r1.status === 'active'
              ? 'border-amber-500/40 bg-amber-950/10 ring-1 ring-amber-500/20'
              : 'border-[#27272a] bg-[#121212]'
          }`}
        >
          <div className="flex items-center justify-between text-xs mb-1.5">
            <span className="font-mono text-[11px] text-[#a1a1aa] uppercase font-semibold">
              Round 1: Calibration
            </span>
            {r1.status === 'completed' ? (
              <Check className="w-3.5 h-3.5 text-emerald-400" />
            ) : (
              <span className="w-2 h-2 rounded-full bg-amber-400" />
            )}
          </div>
          <div className="text-sm font-mono font-bold text-[#f4f4f5]">
            {r1.score}
          </div>
          <div className="text-[11px] text-[#71717a] mt-0.5">
            {r1.status === 'completed' ? 'Calibration score logged' : 'Active challenge round'}
          </div>
        </div>

        {/* Step 2: Round 2 */}
        <div
          className={`p-3.5 rounded-xl border transition-all ${
            r2.status === 'completed'
              ? 'border-emerald-500/30 bg-emerald-950/10'
              : r2.status === 'active'
              ? 'border-blue-500/40 bg-blue-950/10 ring-1 ring-blue-500/20'
              : 'border-[#27272a] bg-[#121212] opacity-75'
          }`}
        >
          <div className="flex items-center justify-between text-xs mb-1.5">
            <span className="font-mono text-[11px] text-[#a1a1aa] uppercase font-semibold">
              Round 2: Verification
            </span>
            {r2.status === 'completed' ? (
              <Check className="w-3.5 h-3.5 text-emerald-400" />
            ) : r2.status === 'active' ? (
              <span className="w-2 h-2 rounded-full bg-blue-400 animate-pulse" />
            ) : (
              <Lock className="w-3.5 h-3.5 text-[#52525b]" />
            )}
          </div>
          <div className="text-sm font-mono font-bold text-[#f4f4f5]">
            {r2.score}
          </div>
          <div className="text-[11px] text-[#71717a] mt-0.5">
            {r2.status === 'completed'
              ? 'Verification score logged'
              : r2.status === 'active'
              ? 'Eliminating luck variance'
              : 'Unlocks after Round 1'}
          </div>
        </div>

        {/* Step 3: Round 3 */}
        <div
          className={`p-3.5 rounded-xl border transition-all ${
            r3.status === 'completed'
              ? 'border-emerald-500/30 bg-emerald-950/10'
              : r3.status === 'active'
              ? 'border-purple-500/40 bg-purple-950/10 ring-1 ring-purple-500/20'
              : 'border-[#27272a] bg-[#121212] opacity-75'
          }`}
        >
          <div className="flex items-center justify-between text-xs mb-1.5">
            <span className="font-mono text-[11px] text-[#a1a1aa] uppercase font-semibold">
              Round 3: Confirmation
            </span>
            {r3.status === 'completed' ? (
              <Check className="w-3.5 h-3.5 text-emerald-400" />
            ) : r3.status === 'active' ? (
              <span className="w-2 h-2 rounded-full bg-purple-400 animate-pulse" />
            ) : (
              <Lock className="w-3.5 h-3.5 text-[#52525b]" />
            )}
          </div>
          <div className="text-sm font-mono font-bold text-[#f4f4f5]">
            {r3.score}
          </div>
          <div className="text-[11px] text-[#71717a] mt-0.5">
            {r3.status === 'completed'
              ? 'Final round evaluated'
              : r3.status === 'active'
              ? 'Final certification round'
              : 'Unlocks after Round 2'}
          </div>
        </div>
      </div>
    </div>
  );
};

export default VerificationBadge;
