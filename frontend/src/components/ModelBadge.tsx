import React, { useState } from 'react';
import {
  CheckCircle2,
  XCircle,
  ChevronDown,
  ChevronUp,
  Brain,
  Zap,
  Cpu,
  Clock,
  Sparkles,
} from 'lucide-react';
import { ModelComparisonResult } from '../api/types';

export interface ModelBadgeProps {
  prediction: ModelComparisonResult;
  winningVariant?: string;
  defaultExpanded?: boolean;
}

/**
 * Format raw model identifier into clean display title.
 */
export function formatModelName(modelName: string): string {
  const lower = modelName.toLowerCase();
  if (lower.includes('frontier')) {
    return 'Frontier Vision';
  }
  if (lower.includes('compact')) {
    return 'Compact Vision';
  }
  if (lower.includes('heuristic')) {
    return 'Heuristic Baseline';
  }
  return modelName
    .replace(/^mock-/, '')
    .replace(/-v\d+.*$/, '')
    .split(/[-_]/)
    .map((w) => w.charAt(0).toUpperCase() + w.slice(1))
    .join(' ');
}

/**
 * Returns tier icon according to model architecture class.
 */
export function getModelTierIcon(modelName: string) {
  const lower = modelName.toLowerCase();
  if (lower.includes('frontier')) {
    return <Brain className="w-4 h-4 text-purple-400" />;
  }
  if (lower.includes('compact')) {
    return <Zap className="w-4 h-4 text-amber-400" />;
  }
  if (lower.includes('heuristic')) {
    return <Cpu className="w-4 h-4 text-cyan-400" />;
  }
  return <Sparkles className="w-4 h-4 text-neutral-400" />;
}

export const ModelBadge: React.FC<ModelBadgeProps> = ({
  prediction,
  defaultExpanded = false,
}) => {
  const [isExpanded, setIsExpanded] = useState<boolean>(defaultExpanded);

  const cleanName = formatModelName(prediction.model_name);
  const tierIcon = getModelTierIcon(prediction.model_name);
  const isCorrect = prediction.is_model_correct;

  // Format confidence percentage (support both 0.0-1.0 and 0-100 formats)
  const confPct =
    prediction.confidence <= 1.0
      ? Math.round(prediction.confidence * 100)
      : Math.round(prediction.confidence);

  // Format latency & cost display
  const latencyDisplay = `${prediction.latency_ms.toLocaleString()}ms`;
  const costDisplay =
    prediction.cost_usd < 0.001
      ? `$${prediction.cost_usd.toFixed(4)}`
      : `$${prediction.cost_usd.toFixed(3)}`;

  return (
    <div
      className={`border rounded-xl transition-all duration-200 bg-[#18181b] ${
        isCorrect
          ? 'border-[#27272a] hover:border-emerald-500/40'
          : 'border-[#27272a] hover:border-rose-500/40'
      } flex flex-col p-4 shadow-sm`}
    >
      {/* Header: Model Identifier & Correct / Wrong Status Badge */}
      <div className="flex items-center justify-between gap-2 mb-2.5">
        <div className="flex items-center space-x-2 min-w-0">
          <div className="p-1 rounded-md bg-[#121212] border border-[#27272a] flex-shrink-0">
            {tierIcon}
          </div>
          <span
            className="font-semibold text-sm text-[#f4f4f5] truncate"
            title={prediction.model_name}
          >
            {cleanName}
          </span>
        </div>

        {/* Status Badge */}
        {isCorrect ? (
          <span className="inline-flex items-center space-x-1 px-2 py-0.5 rounded-full text-xs font-semibold bg-emerald-500/10 text-emerald-400 border border-emerald-500/30 flex-shrink-0">
            <CheckCircle2 className="w-3.5 h-3.5" />
            <span>Correct</span>
          </span>
        ) : (
          <span className="inline-flex items-center space-x-1 px-2 py-0.5 rounded-full text-xs font-semibold bg-rose-500/10 text-rose-400 border border-rose-500/30 flex-shrink-0">
            <XCircle className="w-3.5 h-3.5" />
            <span>Wrong</span>
          </span>
        )}
      </div>

      {/* Middle Row: Predicted Variant + Confidence */}
      <div className="flex items-center justify-between text-xs py-1.5 border-y border-[#27272a]/60 my-1">
        <div className="flex items-center space-x-1.5">
          <span className="text-[#a1a1aa]">Choice:</span>
          <span
            className={`font-mono font-bold px-2 py-0.5 rounded text-xs ${
              prediction.predicted_variant === 'A'
                ? 'bg-amber-500/20 text-amber-300 border border-amber-500/30'
                : 'bg-blue-500/20 text-blue-300 border border-blue-500/30'
            }`}
          >
            Predicted {prediction.predicted_variant}
          </span>
        </div>

        <span
          className="font-mono text-[#a1a1aa]"
          title={`${confPct}% decision confidence`}
        >
          <span className="text-[#f4f4f5] font-semibold">{confPct}%</span> conf
        </span>
      </div>

      {/* Telemetry Tag: Simulated Latency & Cost */}
      <div className="flex items-center justify-between text-[11px] text-[#a1a1aa] mt-2 font-mono">
        <span className="flex items-center space-x-1" title="Inference Latency">
          <Clock className="w-3 h-3 text-neutral-500" />
          <span>{latencyDisplay}</span>
        </span>
        <span
          className="flex items-center space-x-0.5 text-neutral-400"
          title="Simulated Cost per Inference"
        >
          <span>{costDisplay}</span>
          <span className="text-neutral-600 font-sans">/eval</span>
        </span>
      </div>

      {/* Expandable Reasoning Accordion with Tooltip Fallback */}
      <div className="mt-3 pt-2 border-t border-[#27272a]/40">
        <button
          type="button"
          onClick={() => setIsExpanded(!isExpanded)}
          aria-expanded={isExpanded}
          className="w-full flex items-center justify-between text-xs text-[#a1a1aa] hover:text-[#f4f4f5] transition-colors py-1 group"
          title={prediction.reasoning}
        >
          <span className="group-hover:underline">Model Reasoning</span>
          {isExpanded ? (
            <ChevronUp className="w-3.5 h-3.5 text-neutral-400" />
          ) : (
            <ChevronDown className="w-3.5 h-3.5 text-neutral-400" />
          )}
        </button>

        {isExpanded && (
          <div className="mt-2 text-xs text-neutral-300 bg-[#121212] border border-[#27272a] rounded-lg p-3 leading-relaxed">
            <p className="italic text-neutral-300">"{prediction.reasoning}"</p>
            <div className="mt-2.5 pt-2 border-t border-[#27272a]/60 flex items-center justify-between text-[10px] text-neutral-500 font-mono">
              <span>Tokens: {prediction.token_count}</span>
              <span>Prompt: {prediction.prompt_version}</span>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default ModelBadge;
