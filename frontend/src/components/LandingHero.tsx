import React, { useState } from 'react';
import {
  Flame,
  ShieldCheck,
  Cpu,
  Lock,
  ArrowRight,
  CheckCircle2,
  TrendingUp,
  Sparkles,
} from 'lucide-react';

export interface LandingHeroProps {
  onStart: () => void;
}

export const LandingHero: React.FC<LandingHeroProps> = ({ onStart }) => {
  // Interactive mini preview state
  const [selectedMiniVariant, setSelectedMiniVariant] = useState<'A' | 'B' | null>(null);

  return (
    <div className="w-full max-w-4xl mx-auto flex flex-col items-center text-center space-y-10 py-6 sm:py-10 px-2 sm:px-4">
      {/* 1. Top Pill Tag */}
      <div className="inline-flex max-w-full items-center justify-center space-x-2 px-3 sm:px-3.5 py-1.5 rounded-full bg-amber-400/10 border border-amber-400/30 text-amber-300 text-[10px] sm:text-xs font-semibold tracking-wider uppercase shadow-sm shadow-amber-400/5">
        <Flame className="w-3.5 h-3.5 text-amber-400 animate-pulse flex-shrink-0" />
        <span className="text-center">HUMAN VS AI BENCHMARK &bull; EMPIRICAL EVALUATION HARNESS</span>
        <Sparkles className="w-3.5 h-3.5 text-amber-400 flex-shrink-0" />
      </div>

      {/* 2. Primary Headline & Descriptive Hook */}
      <div className="space-y-4 max-w-3xl">
        <h1 className="text-3xl sm:text-5xl lg:text-6xl font-extrabold tracking-tight text-[#f4f4f5] leading-[1.15]">
          Can You Beat{' '}
          <span className="bg-gradient-to-r from-amber-300 via-yellow-200 to-amber-400 bg-clip-text text-transparent">
            Frontier AI
          </span>{' '}
          at Predicting Human Attention?
        </h1>
        <p className="text-[#a1a1aa] text-base sm:text-lg leading-relaxed max-w-2xl mx-auto font-normal">
          In an empirical benchmark of 7,030 human evaluators, frontier multimodal AI outperformed
          98% of participants. But the top 2% of humans crushed the model. Test your perceptual
          intuition across verified real-world YouTube A/B tests.
        </p>
      </div>

      {/* 3. Primary Call to Action */}
      <div className="flex flex-col items-center space-y-3 w-full max-w-md">
        <button
          type="button"
          onClick={onStart}
          className="group w-full py-4 px-8 rounded-xl bg-amber-400 hover:bg-amber-300 text-neutral-950 font-bold text-base sm:text-lg shadow-xl shadow-amber-400/20 hover:shadow-amber-400/40 transition-all duration-200 transform hover:-translate-y-0.5 active:translate-y-0 flex items-center justify-center space-x-3 cursor-pointer"
        >
          <span>Start Round 1 Calibration (~30s)</span>
          <ArrowRight className="w-5 h-5 transition-transform duration-200 group-hover:translate-x-1" />
        </button>
        <p className="text-xs sm:text-sm text-[#a1a1aa] font-medium tracking-wide">
          No signup required &bull; 10 unseen challenges &bull; Instant ground-truth receipts
        </p>
      </div>

      {/* 4. Interactive Mini Preview Box */}
      <div className="w-full rounded-2xl bg-[#18181b] border border-[#27272a] p-4 sm:p-6 text-left shadow-2xl relative overflow-hidden">
        {/* Subtle background glow */}
        <div className="absolute -top-24 -right-24 w-60 h-60 bg-amber-400/5 rounded-full blur-3xl pointer-events-none" />

        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 pb-4 border-b border-[#27272a]">
          <div className="flex items-center space-x-2">
            <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
            <span className="text-xs font-mono font-semibold text-[#f4f4f5] tracking-wide uppercase">
              Interactive Mini Preview
            </span>
            <span className="text-xs text-[#a1a1aa]">• Sample Real YouTube Split-Test</span>
          </div>
          <div className="text-[11px] font-mono text-[#a1a1aa] bg-[#121212] px-2.5 py-1 rounded-md border border-[#27272a]">
            Sample N = 84,200 impressions
          </div>
        </div>

        <p className="text-xs sm:text-sm text-[#f4f4f5] font-medium mt-3 mb-4">
          Which thumbnail drove +31.4% higher click-through rate in a verified YouTube A/B test?
          <span className="block text-xs text-[#a1a1aa] font-normal mt-0.5">
            Tap Option A or Option B below for an instant gameplay preview:
          </span>
        </p>

        {/* Side-by-side miniature comparison card */}
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 sm:gap-4">
          {/* Option A Mini Card */}
          <button
            type="button"
            onClick={() => setSelectedMiniVariant('A')}
            className={`group text-left p-3.5 rounded-xl border transition-all duration-200 relative cursor-pointer ${
              selectedMiniVariant === 'A'
                ? 'bg-[#222226] border-amber-400 shadow-md shadow-amber-400/10'
                : 'bg-[#121212] border-[#27272a] hover:border-[#3f3f46]'
            }`}
          >
            <div className="flex items-center justify-between mb-2.5">
              <span className="text-xs font-bold text-amber-400 px-2 py-0.5 rounded bg-amber-400/10 border border-amber-400/20">
                Option A
              </span>
              {selectedMiniVariant === 'A' && (
                <span className="flex items-center space-x-1 text-[11px] text-amber-300 font-semibold">
                  <CheckCircle2 className="w-3.5 h-3.5" />
                  <span>Your Pick</span>
                </span>
              )}
            </div>

            {/* Stylized Miniature Thumbnail Mock */}
            <div className="aspect-video w-full rounded-lg bg-gradient-to-br from-neutral-900 via-neutral-800 to-rose-950/60 border border-[#27272a] p-3 flex flex-col justify-between overflow-hidden relative">
              <div className="flex items-center justify-between">
                <span className="text-[10px] font-mono bg-red-600/90 text-white font-bold px-1.5 py-0.5 rounded uppercase tracking-wider">
                  Critical
                </span>
                <TrendingUp className="w-4 h-4 text-rose-400" />
              </div>
              <div>
                <p className="text-xs sm:text-sm font-black text-white leading-tight drop-shadow">
                  WHY 99% OF APPS FAIL IN PRODUCTION
                </p>
                <p className="text-[10px] text-rose-300 font-mono mt-0.5">
                  High Emotion • Bold Text Contrast
                </p>
              </div>
            </div>
          </button>

          {/* Option B Mini Card */}
          <button
            type="button"
            onClick={() => setSelectedMiniVariant('B')}
            className={`group text-left p-3.5 rounded-xl border transition-all duration-200 relative cursor-pointer ${
              selectedMiniVariant === 'B'
                ? 'bg-[#222226] border-amber-400 shadow-md shadow-amber-400/10'
                : 'bg-[#121212] border-[#27272a] hover:border-[#3f3f46]'
            }`}
          >
            <div className="flex items-center justify-between mb-2.5">
              <span className="text-xs font-bold text-[#a1a1aa] px-2 py-0.5 rounded bg-neutral-800 border border-[#27272a]">
                Option B
              </span>
              {selectedMiniVariant === 'B' && (
                <span className="flex items-center space-x-1 text-[11px] text-amber-300 font-semibold">
                  <CheckCircle2 className="w-3.5 h-3.5" />
                  <span>Your Pick</span>
                </span>
              )}
            </div>

            {/* Stylized Miniature Thumbnail Mock */}
            <div className="aspect-video w-full rounded-lg bg-gradient-to-br from-neutral-900 via-neutral-800 to-blue-950/60 border border-[#27272a] p-3 flex flex-col justify-between overflow-hidden relative">
              <div className="flex items-center justify-between">
                <span className="text-[10px] font-mono bg-blue-600/90 text-white font-bold px-1.5 py-0.5 rounded uppercase tracking-wider">
                  Architecture
                </span>
                <Cpu className="w-4 h-4 text-blue-400" />
              </div>
              <div>
                <p className="text-xs sm:text-sm font-black text-white leading-tight drop-shadow">
                  System Design &amp; Microservices Guide
                </p>
                <p className="text-[10px] text-blue-300 font-mono mt-0.5">
                  Technical Diagram • Neutral Tone
                </p>
              </div>
            </div>
          </button>
        </div>

        {/* Simulated Model Comparison Pill & Live Mini Outcome */}
        <div className="mt-4 pt-3.5 border-t border-[#27272a] flex flex-col sm:flex-row sm:items-center justify-between gap-3">
          <div className="inline-flex items-center space-x-2 px-3 py-1.5 rounded-lg bg-[#121212] border border-[#27272a] text-xs">
            <Cpu className="w-3.5 h-3.5 text-blue-400 flex-shrink-0" />
            <span className="text-[#a1a1aa]">Frontier Baseline (GPT-4o Vision):</span>
            <span className="font-semibold text-emerald-400">Option A (84% conf)</span>
          </div>

          {selectedMiniVariant ? (
            <div className="text-xs text-[#f4f4f5] bg-emerald-500/10 border border-emerald-500/30 px-3 py-1.5 rounded-lg flex items-center space-x-2">
              <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400 flex-shrink-0" />
              <span>
                {selectedMiniVariant === 'A'
                  ? 'Correct! Option A won with 6.8% vs 5.2% CTR (p < 0.001).'
                  : 'Option A actually won (+31% CTR, p < 0.001). Model beat you here!'}
              </span>
            </div>
          ) : (
            <div className="text-xs text-[#a1a1aa] italic">
              Click Option A or B above to preview instant ground-truth receipt.
            </div>
          )}
        </div>
      </div>

      {/* 5. 3 Trust/Depth Stat Badges */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 w-full text-left">
        {/* Badge 1: Statistical Significance */}
        <div className="p-4 rounded-xl bg-[#18181b] border border-[#27272a] flex flex-col space-y-2">
          <div className="flex items-center space-x-2.5">
            <div className="p-2 rounded-lg bg-amber-400/10 text-amber-400 border border-amber-400/20">
              <ShieldCheck className="w-4 h-4" />
            </div>
            <span className="font-bold text-sm text-[#f4f4f5]">p &lt; 0.05 Certified</span>
          </div>
          <p className="text-xs text-[#a1a1aa] leading-relaxed">
            Every A/B test enforced at N &ge; 20,000 impressions with two-proportion z-tests.
          </p>
        </div>

        {/* Badge 2: Frontier Model Baselines */}
        <div className="p-4 rounded-xl bg-[#18181b] border border-[#27272a] flex flex-col space-y-2">
          <div className="flex items-center space-x-2.5">
            <div className="p-2 rounded-lg bg-blue-500/10 text-blue-400 border border-blue-500/20">
              <Cpu className="w-4 h-4" />
            </div>
            <span className="font-bold text-sm text-[#f4f4f5]">Frontier Model Baselines</span>
          </div>
          <p className="text-xs text-[#a1a1aa] leading-relaxed">
            Pinned multimodal evaluation runner logging tokens, latency, and costs.
          </p>
        </div>

        {/* Badge 3: Cryptographic Verification */}
        <div className="p-4 rounded-xl bg-[#18181b] border border-[#27272a] flex flex-col space-y-2">
          <div className="flex items-center space-x-2.5">
            <div className="p-2 rounded-lg bg-purple-500/10 text-purple-400 border border-purple-500/20">
              <Lock className="w-4 h-4" />
            </div>
            <span className="font-bold text-sm text-[#f4f4f5]">Cryptographic Verification</span>
          </div>
          <p className="text-xs text-[#a1a1aa] leading-relaxed">
            3-round unseen challenge track with tamper-evident SHA-256 receipts.
          </p>
        </div>
      </div>
    </div>
  );
};

export default LandingHero;
