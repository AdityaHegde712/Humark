import React, { useEffect, useState } from 'react';
import {
  CheckCircle2,
  XCircle,
  Crown,
  ArrowRight,
  TrendingUp,
  ShieldCheck,
  Image as ImageIcon,
  Check,
} from 'lucide-react';
import { AttemptReceipt } from '../api/types';
import ModelBadge from './ModelBadge';

export interface ReceiptModalProps {
  receipt: AttemptReceipt;
  onNext: () => void;
  isLoadingNext?: boolean;
}

export const ReceiptModal: React.FC<ReceiptModalProps> = ({
  receipt,
  onNext,
  isLoadingNext = false,
}) => {
  const [imgAError, setImgAError] = useState<boolean>(false);
  const [imgBError, setImgBError] = useState<boolean>(false);

  // Compute beats against baseline AI models
  const beatenCount = receipt.is_correct
    ? receipt.model_predictions.filter((m) => !m.is_model_correct).length
    : 0;
  const totalModels = receipt.model_predictions.length || 3;

  // Compute relative performance differential of winner over loser
  const winningCtr = receipt.winning_variant === 'A' ? receipt.ctr_a : receipt.ctr_b;
  const losingCtr = receipt.winning_variant === 'A' ? receipt.ctr_b : receipt.ctr_a;
  const relativeDiff =
    losingCtr > 0
      ? (((winningCtr - losingCtr) / losingCtr) * 100).toFixed(1)
      : '0.0';

  // Keyboard navigation listener (Enter or Space advances to next challenge)
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      // Disregard keyboard events when user is in input/textarea
      const target = e.target as HTMLElement;
      if (target && (target.tagName === 'INPUT' || target.tagName === 'TEXTAREA')) {
        return;
      }

      if (e.key === 'Enter' || e.key === ' ') {
        e.preventDefault();
        if (!isLoadingNext) {
          onNext();
        }
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [onNext, isLoadingNext]);

  return (
    <div
      className="fixed inset-0 z-50 bg-black/85 backdrop-blur-md flex items-center justify-center p-3 sm:p-6 overflow-y-auto"
      role="dialog"
      aria-modal="true"
      aria-labelledby="receipt-outcome-title"
    >
      <div className="w-full max-w-4xl bg-[#141417] border border-[#27272a] rounded-2xl shadow-2xl overflow-hidden my-auto flex flex-col max-h-[94vh]">
        {/* Outcome Banner */}
        <div
          className={`p-5 sm:p-6 border-b flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 ${
            receipt.is_correct
              ? 'bg-emerald-950/30 border-emerald-500/30 text-emerald-300'
              : 'bg-rose-950/30 border-rose-500/30 text-rose-300'
          }`}
        >
          <div className="flex items-center space-x-3.5">
            <div
              className={`w-12 h-12 rounded-xl flex items-center justify-center flex-shrink-0 border ${
                receipt.is_correct
                  ? 'bg-emerald-500/20 border-emerald-500/30 text-emerald-400'
                  : 'bg-rose-500/20 border-rose-500/30 text-rose-400'
              }`}
            >
              {receipt.is_correct ? (
                <CheckCircle2 className="w-7 h-7 stroke-[2.5]" />
              ) : (
                <XCircle className="w-7 h-7 stroke-[2.5]" />
              )}
            </div>
            <div>
              <h2
                id="receipt-outcome-title"
                className="text-lg sm:text-xl font-bold text-[#f4f4f5] tracking-tight"
              >
                {receipt.is_correct
                  ? 'Correct! You predicted the winning thumbnail.'
                  : 'Incorrect. The audience preferred the other variant.'}
              </h2>
              <p className="text-xs sm:text-sm text-[#a1a1aa] mt-0.5">
                You beat{' '}
                <span className="font-semibold text-[#f4f4f5]">
                  {beatenCount} of {totalModels}
                </span>{' '}
                AI models on this challenge.
              </p>
            </div>
          </div>

          <div className="flex items-center space-x-2 self-end sm:self-center">
            <span className="text-xs font-mono px-3 py-1 rounded-full bg-[#18181b] border border-[#27272a] text-[#a1a1aa]">
              Challenge {receipt.attempt_index} of {receipt.round_items}
            </span>
          </div>
        </div>

        {/* Modal Scrollable Body */}
        <div className="p-4 sm:p-6 space-y-6 overflow-y-auto flex-1">
          {/* Challenge Title & Relative Performance Differential */}
          <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 border-b border-[#27272a]/60 pb-4">
            <div className="min-w-0">
              <span className="text-[11px] font-mono uppercase tracking-wider text-amber-400">
                Ground Truth Split Test
              </span>
              <h3 className="text-base sm:text-lg font-semibold text-[#f4f4f5] truncate">
                {receipt.title}
              </h3>
            </div>

            <div className="flex-shrink-0 inline-flex items-center space-x-1.5 px-3 py-1.5 rounded-lg bg-emerald-500/10 border border-emerald-500/25 text-emerald-300 text-xs font-mono font-semibold">
              <TrendingUp className="w-4 h-4 text-emerald-400" />
              <span>+{relativeDiff}% higher click-through</span>
            </div>
          </div>

          {/* Side-by-Side Variant Breakdown */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {/* Variant A Card */}
            <div
              className={`relative rounded-xl border p-4 flex flex-col justify-between transition-all ${
                receipt.winning_variant === 'A'
                  ? 'border-amber-400/80 bg-amber-500/[0.04] ring-1 ring-amber-400/40 shadow-lg'
                  : 'border-[#27272a] bg-[#18181b]'
              }`}
            >
              {/* Header: Option Tag + Ground Truth / Pick Badges */}
              <div className="flex items-center justify-between gap-2 mb-3">
                <div className="flex items-center space-x-2">
                  <span className="text-xs font-bold px-2 py-0.5 rounded bg-amber-500/20 text-amber-300 border border-amber-500/30">
                    VARIANT A
                  </span>
                  {receipt.selected_variant === 'A' && (
                    <span className="text-xs font-semibold px-2 py-0.5 rounded bg-[#27272a] text-[#f4f4f5] border border-neutral-600 flex items-center space-x-1">
                      <Check className="w-3 h-3 text-neutral-300" />
                      <span>Your Pick</span>
                    </span>
                  )}
                </div>

                {receipt.winning_variant === 'A' && (
                  <span className="px-2.5 py-0.5 rounded bg-amber-400 text-black font-extrabold text-[11px] flex items-center space-x-1 shadow-sm">
                    <Crown className="w-3.5 h-3.5 fill-black" />
                    <span>GROUND TRUTH WINNER</span>
                  </span>
                )}
              </div>

              {/* Thumbnail Container */}
              <div className="aspect-video w-full rounded-lg bg-[#121212] border border-[#27272a] overflow-hidden flex items-center justify-center relative mb-3">
                {!imgAError ? (
                  <img
                    src={receipt.thumbnail_a_url}
                    alt={`${receipt.title} - Variant A`}
                    onError={() => setImgAError(true)}
                    className="w-full h-full object-cover"
                  />
                ) : (
                  <div className="flex flex-col items-center justify-center text-neutral-500 space-y-1 p-4">
                    <ImageIcon className="w-7 h-7 text-neutral-600" />
                    <span className="text-xs font-mono">Variant A Preview</span>
                  </div>
                )}
              </div>

              {/* Exact Metrics */}
              <div className="space-y-1.5 pt-2 border-t border-[#27272a]/60 font-mono">
                <div className="flex items-baseline justify-between">
                  <span className="text-xs text-[#a1a1aa] font-sans">Click-Through Rate</span>
                  <span
                    className={`text-lg font-bold ${
                      receipt.winning_variant === 'A' ? 'text-amber-400' : 'text-[#f4f4f5]'
                    }`}
                  >
                    {(receipt.ctr_a * 100).toFixed(2)}% CTR
                  </span>
                </div>
                <div className="flex items-center justify-between text-xs text-[#a1a1aa]">
                  <span>Impressions & Clicks</span>
                  <span className="text-neutral-300">
                    {receipt.impressions_a.toLocaleString()} imp &bull;{' '}
                    {receipt.clicks_a.toLocaleString()} clicks
                  </span>
                </div>
              </div>
            </div>

            {/* Variant B Card */}
            <div
              className={`relative rounded-xl border p-4 flex flex-col justify-between transition-all ${
                receipt.winning_variant === 'B'
                  ? 'border-amber-400/80 bg-amber-500/[0.04] ring-1 ring-amber-400/40 shadow-lg'
                  : 'border-[#27272a] bg-[#18181b]'
              }`}
            >
              {/* Header: Option Tag + Ground Truth / Pick Badges */}
              <div className="flex items-center justify-between gap-2 mb-3">
                <div className="flex items-center space-x-2">
                  <span className="text-xs font-bold px-2 py-0.5 rounded bg-blue-500/20 text-blue-300 border border-blue-500/30">
                    VARIANT B
                  </span>
                  {receipt.selected_variant === 'B' && (
                    <span className="text-xs font-semibold px-2 py-0.5 rounded bg-[#27272a] text-[#f4f4f5] border border-neutral-600 flex items-center space-x-1">
                      <Check className="w-3 h-3 text-neutral-300" />
                      <span>Your Pick</span>
                    </span>
                  )}
                </div>

                {receipt.winning_variant === 'B' && (
                  <span className="px-2.5 py-0.5 rounded bg-amber-400 text-black font-extrabold text-[11px] flex items-center space-x-1 shadow-sm">
                    <Crown className="w-3.5 h-3.5 fill-black" />
                    <span>GROUND TRUTH WINNER</span>
                  </span>
                )}
              </div>

              {/* Thumbnail Container */}
              <div className="aspect-video w-full rounded-lg bg-[#121212] border border-[#27272a] overflow-hidden flex items-center justify-center relative mb-3">
                {!imgBError ? (
                  <img
                    src={receipt.thumbnail_b_url}
                    alt={`${receipt.title} - Variant B`}
                    onError={() => setImgBError(true)}
                    className="w-full h-full object-cover"
                  />
                ) : (
                  <div className="flex flex-col items-center justify-center text-neutral-500 space-y-1 p-4">
                    <ImageIcon className="w-7 h-7 text-neutral-600" />
                    <span className="text-xs font-mono">Variant B Preview</span>
                  </div>
                )}
              </div>

              {/* Exact Metrics */}
              <div className="space-y-1.5 pt-2 border-t border-[#27272a]/60 font-mono">
                <div className="flex items-baseline justify-between">
                  <span className="text-xs text-[#a1a1aa] font-sans">Click-Through Rate</span>
                  <span
                    className={`text-lg font-bold ${
                      receipt.winning_variant === 'B' ? 'text-amber-400' : 'text-[#f4f4f5]'
                    }`}
                  >
                    {(receipt.ctr_b * 100).toFixed(2)}% CTR
                  </span>
                </div>
                <div className="flex items-center justify-between text-xs text-[#a1a1aa]">
                  <span>Impressions & Clicks</span>
                  <span className="text-neutral-300">
                    {receipt.impressions_b.toLocaleString()} imp &bull;{' '}
                    {receipt.clicks_b.toLocaleString()} clicks
                  </span>
                </div>
              </div>
            </div>
          </div>

          {/* Statistical Provenance Box */}
          <div className="border border-[#27272a] bg-[#18181b] rounded-xl p-4 sm:p-5 space-y-3">
            <div className="flex items-center justify-between">
              <div className="flex items-center space-x-2">
                <ShieldCheck className="w-4 h-4 text-emerald-400" />
                <span className="text-xs font-bold uppercase tracking-wider text-[#f4f4f5]">
                  Statistical Provenance
                </span>
              </div>
              <span className="text-[11px] font-mono px-2 py-0.5 rounded bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                p &lt; 0.05 Certified
              </span>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 text-xs font-mono pt-1">
              <div className="bg-[#121212] p-2.5 rounded-lg border border-[#27272a]">
                <div className="text-[11px] text-[#a1a1aa] font-sans">Two-Proportion Z-Score</div>
                <div className="text-sm font-bold text-[#f4f4f5] mt-0.5">
                  z = {receipt.z_score >= 0 ? '+' : ''}
                  {receipt.z_score.toFixed(2)}
                </div>
              </div>

              <div className="bg-[#121212] p-2.5 rounded-lg border border-[#27272a]">
                <div className="text-[11px] text-[#a1a1aa] font-sans">Exact P-Value</div>
                <div className="text-sm font-bold text-emerald-400 mt-0.5">
                  p = {receipt.p_value < 0.0001 ? '< 0.0001' : receipt.p_value.toFixed(4)}
                </div>
              </div>

              <div className="bg-[#121212] p-2.5 rounded-lg border border-[#27272a]">
                <div className="text-[11px] text-[#a1a1aa] font-sans">Source Provenance</div>
                <div className="text-sm font-semibold text-[#f4f4f5] mt-0.5 truncate" title={receipt.provenance_source}>
                  {receipt.provenance_source}
                </div>
              </div>
            </div>

            <p className="text-xs text-[#a1a1aa] leading-relaxed pt-1">
              Meets Humark p &lt; 0.05 statistical significance threshold with N &ge; 20,000 impressions per variant.
            </p>
          </div>

          {/* AI Model Baseline Grid / Row */}
          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <h4 className="text-xs font-bold uppercase tracking-wider text-[#a1a1aa]">
                AI Model Predictions ({receipt.model_predictions.length} Evaluated)
              </h4>
              <span className="text-[11px] text-[#a1a1aa]">
                Vision baselines scored against ground truth
              </span>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
              {receipt.model_predictions.map((pred) => (
                <ModelBadge
                  key={pred.model_name}
                  prediction={pred}
                  winningVariant={receipt.winning_variant}
                />
              ))}
            </div>
          </div>
        </div>

        {/* Modal Footer / Primary Action Button */}
        <div className="p-4 sm:p-5 border-t border-[#27272a] bg-[#121212] flex flex-col sm:flex-row items-center justify-between gap-3">
          <div className="text-xs text-[#a1a1aa] hidden sm:flex items-center space-x-1.5">
            <span>Press</span>
            <kbd className="px-2 py-0.5 rounded bg-[#27272a] text-[#f4f4f5] font-mono text-xs font-bold border border-neutral-700">
              Enter
            </kbd>
            <span>or</span>
            <kbd className="px-2 py-0.5 rounded bg-[#27272a] text-[#f4f4f5] font-mono text-xs font-bold border border-neutral-700">
              Space
            </kbd>
            <span>to advance to the next challenge</span>
          </div>

          <button
            type="button"
            onClick={onNext}
            disabled={isLoadingNext}
            className="w-full sm:w-auto px-7 py-3 rounded-xl bg-amber-400 hover:bg-amber-300 text-black font-bold text-sm transition-all duration-150 flex items-center justify-center space-x-2 shadow-lg disabled:opacity-50"
          >
            <span>{isLoadingNext ? 'Loading Next...' : 'Next Challenge'}</span>
            <ArrowRight className="w-4 h-4 stroke-[2.5]" />
          </button>
        </div>
      </div>
    </div>
  );
};

export default ReceiptModal;
