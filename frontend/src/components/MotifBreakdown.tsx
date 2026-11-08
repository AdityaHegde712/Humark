import React from 'react';
import {
  Brain,
  Sparkles,
  Bot,
  User,
  CheckCircle2,
  TrendingUp,
  Scale,
  Eye,
  Type,
  HelpCircle,
  Layers,
} from 'lucide-react';
import { MotifPerformanceItem } from '../api/types';

export interface MotifBreakdownProps {
  items?: MotifPerformanceItem[];
  className?: string;
}

export const MotifBreakdown: React.FC<MotifBreakdownProps> = ({
  items = [],
  className = '',
}) => {
  if (!items || items.length === 0) {
    return null;
  }

  // Separate motifs into perceptual strengths vs algorithmic strengths
  const humanStrengths = items.filter(
    (item) => item.accuracy_delta > 0.05 || (item.accuracy_delta > 0 && item.verdict !== 'ai_dominant')
  );
  const aiStrengths = items.filter(
    (item) => item.accuracy_delta < -0.05 || (item.accuracy_delta < 0 && item.verdict !== 'human_dominant')
  );
  const parityItems = items.filter(
    (item) => Math.abs(item.accuracy_delta) <= 0.05 && !humanStrengths.includes(item) && !aiStrengths.includes(item)
  );

  const getMotifIcon = (motif: string) => {
    switch (motif) {
      case 'face_emotion':
        return <Eye className="w-4 h-4 text-amber-400" />;
      case 'curiosity_gap':
        return <HelpCircle className="w-4 h-4 text-amber-400" />;
      case 'text_contrast':
        return <Type className="w-4 h-4 text-purple-400" />;
      case 'visual_complexity':
        return <Layers className="w-4 h-4 text-purple-400" />;
      default:
        return <Sparkles className="w-4 h-4 text-neutral-400" />;
    }
  };

  const renderMotifCard = (item: MotifPerformanceItem) => {
    const humanPct = (item.user_accuracy * 100).toFixed(1);
    const frontierPct = (item.frontier_accuracy * 100).toFixed(1);
    const deltaPct = Math.abs(item.accuracy_delta * 100).toFixed(1);

    return (
      <div
        key={item.motif}
        className="p-5 rounded-xl border border-[#27272a] bg-[#121212] space-y-4 hover:border-neutral-700 transition-colors"
      >
        {/* Card Header */}
        <div className="flex items-center justify-between gap-3">
          <div className="flex items-center space-x-2.5">
            <div className="w-8 h-8 rounded-lg bg-[#18181b] border border-[#27272a] flex items-center justify-center">
              {getMotifIcon(item.motif)}
            </div>
            <div>
              <div className="font-bold text-[#f4f4f5] text-base">{item.motif_name}</div>
              <div className="text-[11px] font-mono text-[#71717a]">
                Sample: n={item.total_attempts} items
              </div>
            </div>
          </div>

          {/* Advantage Badge */}
          {item.verdict === 'human_dominant' ? (
            <span className="inline-flex items-center space-x-1 px-2.5 py-1 rounded-full text-xs font-mono font-bold bg-amber-500/10 text-amber-400 border border-amber-500/30">
              <TrendingUp className="w-3 h-3" />
              <span>+{deltaPct}% Human Edge</span>
            </span>
          ) : item.verdict === 'ai_dominant' ? (
            <span className="inline-flex items-center space-x-1 px-2.5 py-1 rounded-full text-xs font-mono font-bold bg-purple-500/10 text-purple-400 border border-purple-500/30">
              <Bot className="w-3 h-3" />
              <span>+{deltaPct}% AI Edge</span>
            </span>
          ) : (
            <span className="inline-flex items-center space-x-1 px-2.5 py-1 rounded-full text-xs font-mono font-semibold bg-neutral-800 text-neutral-300 border border-neutral-700">
              <Scale className="w-3 h-3" />
              <span>Parity ({deltaPct}%)</span>
            </span>
          )}
        </div>

        {/* Visual Progress Bars */}
        <div className="space-y-2.5 pt-1">
          {/* Human Accuracy Bar */}
          <div className="space-y-1">
            <div className="flex items-center justify-between text-xs font-mono">
              <div className="flex items-center space-x-1.5 text-amber-400 font-medium">
                <User className="w-3.5 h-3.5" />
                <span>You (Human)</span>
              </div>
              <span className="font-bold text-[#f4f4f5]">{humanPct}%</span>
            </div>
            <div className="w-full h-2.5 rounded-full bg-[#18181b] overflow-hidden border border-[#27272a]">
              <div
                className="h-full bg-gradient-to-r from-amber-500 to-amber-400 rounded-full transition-all duration-500"
                style={{ width: `${Math.min(100, Math.max(0, item.user_accuracy * 100))}%` }}
              />
            </div>
          </div>

          {/* Frontier AI Accuracy Bar */}
          <div className="space-y-1">
            <div className="flex items-center justify-between text-xs font-mono">
              <div className="flex items-center space-x-1.5 text-purple-400 font-medium">
                <Bot className="w-3.5 h-3.5" />
                <span>Frontier AI</span>
              </div>
              <span className="font-bold text-[#f4f4f5]">{frontierPct}%</span>
            </div>
            <div className="w-full h-2.5 rounded-full bg-[#18181b] overflow-hidden border border-[#27272a]">
              <div
                className="h-full bg-gradient-to-r from-purple-600 to-purple-400 rounded-full transition-all duration-500"
                style={{ width: `${Math.min(100, Math.max(0, item.frontier_accuracy * 100))}%` }}
              />
            </div>
          </div>
        </div>

        {/* Psychological Insight Box */}
        <div className="p-3 rounded-lg bg-[#18181b]/80 border border-[#27272a] text-xs text-[#a1a1aa] leading-relaxed">
          <div className="flex items-start space-x-2">
            <Brain className="w-3.5 h-3.5 text-neutral-400 flex-shrink-0 mt-0.5" />
            <p className="italic">{item.insight}</p>
          </div>
        </div>
      </div>
    );
  };

  return (
    <div className={`rounded-2xl border border-[#27272a] bg-[#18181b] p-6 sm:p-8 space-y-6 ${className}`}>
      {/* Header */}
      <div>
        <div className="text-xs font-mono uppercase tracking-widest text-[#a1a1aa] mb-1">
          Visual Motif &amp; Failure-Mode Analysis
        </div>
        <h3 className="text-xl font-bold text-[#f4f4f5]">
          Where Human Intuition Beats Frontier AI
        </h3>
        <p className="text-xs text-[#a1a1aa] mt-1">
          Cognitive visual reasoning vs automated multimodal models across specific thumbnail design motifs
        </p>
      </div>

      {/* Two Curated Grid Sections */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Column 1: Human Perceptual Strengths */}
        <div className="space-y-4">
          <div className="flex items-center space-x-2">
            <span className="w-2.5 h-2.5 rounded-full bg-amber-400" />
            <h4 className="text-sm font-bold uppercase tracking-wider text-amber-300">
              Human Perceptual Strengths
            </h4>
            <span className="text-xs font-mono text-[#71717a]">
              ({humanStrengths.length})
            </span>
          </div>

          {humanStrengths.length > 0 ? (
            <div className="space-y-3">
              {humanStrengths.map((item) => renderMotifCard(item))}
            </div>
          ) : (
            <div className="p-6 rounded-xl border border-dashed border-[#27272a] bg-[#121212] text-center text-xs text-[#71717a] space-y-1">
              <CheckCircle2 className="w-6 h-6 mx-auto text-neutral-600 mb-2" />
              <p className="font-semibold text-neutral-400">No Human Advantage Detected Yet</p>
              <p>Continue solving challenges to unlock perceptual failure-mode telemetry.</p>
            </div>
          )}
        </div>

        {/* Column 2: AI Algorithmic Strengths */}
        <div className="space-y-4">
          <div className="flex items-center space-x-2">
            <span className="w-2.5 h-2.5 rounded-full bg-purple-400" />
            <h4 className="text-sm font-bold uppercase tracking-wider text-purple-300">
              AI Algorithmic Strengths
            </h4>
            <span className="text-xs font-mono text-[#71717a]">
              ({aiStrengths.length})
            </span>
          </div>

          {aiStrengths.length > 0 ? (
            <div className="space-y-3">
              {aiStrengths.map((item) => renderMotifCard(item))}
            </div>
          ) : (
            <div className="p-6 rounded-xl border border-dashed border-[#27272a] bg-[#121212] text-center text-xs text-[#71717a] space-y-1">
              <Bot className="w-6 h-6 mx-auto text-neutral-600 mb-2" />
              <p className="font-semibold text-neutral-400">Zero AI Dominance Detected</p>
              <p>Frontier AI has not outperformed your selections in any evaluated motifs.</p>
            </div>
          )}
        </div>
      </div>

      {/* Optional Parity Section if any */}
      {parityItems.length > 0 && (
        <div className="pt-2 border-t border-[#27272a]/80 space-y-3">
          <div className="flex items-center space-x-2">
            <Scale className="w-4 h-4 text-neutral-400" />
            <h4 className="text-xs font-bold uppercase tracking-wider text-neutral-400">
              Perceptual Parity (&plusmn;5% Delta)
            </h4>
            <span className="text-xs font-mono text-[#71717a]">
              ({parityItems.length})
            </span>
          </div>
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
            {parityItems.map((item) => renderMotifCard(item))}
          </div>
        </div>
      )}
    </div>
  );
};

export default MotifBreakdown;
