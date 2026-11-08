import React, { useEffect, useRef, useState, useCallback } from 'react';
import { Clock, Image as ImageIcon, Sparkles, Check } from 'lucide-react';

export interface ChallengeCardProps {
  challengeId: string;
  title: string;
  category: string;
  thumbnailAUrl: string;
  thumbnailBUrl: string;
  onSelect: (variant: 'A' | 'B', latencyMs: number) => void;
  isSubmitting?: boolean;
  disabled?: boolean;
}

export const ChallengeCard: React.FC<ChallengeCardProps> = ({
  challengeId,
  title,
  category,
  thumbnailAUrl,
  thumbnailBUrl,
  onSelect,
  isSubmitting = false,
  disabled = false,
}) => {
  const startTimeRef = useRef<number>(performance.now());
  const [elapsedMs, setElapsedMs] = useState<number>(0);
  const [selectedVariant, setSelectedVariant] = useState<'A' | 'B' | null>(null);
  const [imgAError, setImgAError] = useState<boolean>(false);
  const [imgBError, setImgBError] = useState<boolean>(false);

  // Reset timer on new challenge
  useEffect(() => {
    startTimeRef.current = performance.now();
    setElapsedMs(0);
    setSelectedVariant(null);
    setImgAError(false);
    setImgBError(false);

    const interval = setInterval(() => {
      setElapsedMs(Math.round(performance.now() - startTimeRef.current));
    }, 50);

    return () => clearInterval(interval);
  }, [challengeId]);

  // Selection callback handler
  const handleSelect = useCallback(
    (variant: 'A' | 'B') => {
      if (disabled || isSubmitting || selectedVariant !== null) return;
      const latency = Math.max(1, Math.round(performance.now() - startTimeRef.current));
      setSelectedVariant(variant);
      onSelect(variant, latency);
    },
    [disabled, isSubmitting, selectedVariant, onSelect]
  );

  // Keyboard navigation listener (Keys 1 / A for Variant A, Keys 2 / B for Variant B)
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (disabled || isSubmitting || selectedVariant !== null) return;

      // Ignore keystrokes in active input fields
      const target = e.target as HTMLElement;
      if (target && (target.tagName === 'INPUT' || target.tagName === 'TEXTAREA')) {
        return;
      }

      const isOptionA =
        e.key === '1' ||
        e.code === 'Digit1' ||
        e.code === 'Numpad1' ||
        e.key.toLowerCase() === 'a' ||
        e.code === 'KeyA';

      const isOptionB =
        e.key === '2' ||
        e.code === 'Digit2' ||
        e.code === 'Numpad2' ||
        e.key.toLowerCase() === 'b' ||
        e.code === 'KeyB';

      if (isOptionA) {
        e.preventDefault();
        handleSelect('A');
      } else if (isOptionB) {
        e.preventDefault();
        handleSelect('B');
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [disabled, isSubmitting, selectedVariant, handleSelect]);

  // Format category badge
  const formattedCategory =
    category === 'youtube_thumbnails'
      ? 'YouTube Thumbnails'
      : category.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase());

  // Seconds formatter for latency counter
  const secondsDisplay = (elapsedMs / 1000).toFixed(2);

  return (
    <div className="w-full max-w-6xl mx-auto flex flex-col space-y-6">
      {/* Challenge Header & Category Metadata */}
      <div className="border border-[#27272a] bg-[#18181b] rounded-xl p-5 md:p-6 shadow-sm">
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 mb-2">
          <div className="flex items-center space-x-2">
            <span className="text-xs font-semibold px-2.5 py-1 rounded-md bg-amber-500/10 text-amber-400 border border-amber-500/20 uppercase tracking-wide">
              {formattedCategory}
            </span>
            <span className="text-xs text-[#a1a1aa] flex items-center space-x-1">
              <Sparkles className="w-3.5 h-3.5 text-blue-400" />
              <span>A/B Split Test Winner</span>
            </span>
          </div>

          {/* Decision Latency Counter */}
          <div className="flex items-center space-x-1.5 text-xs font-mono border border-[#27272a] bg-[#121212] px-3 py-1 rounded-md text-[#a1a1aa] self-start sm:self-auto">
            <Clock className="w-3.5 h-3.5 text-neutral-400" />
            <span>Decision Time:</span>
            <span className="text-amber-400 font-semibold">{secondsDisplay}s</span>
          </div>
        </div>

        <h1 className="text-lg md:text-xl font-bold tracking-tight text-[#f4f4f5]">
          {title}
        </h1>
        <p className="text-xs md:text-sm text-[#a1a1aa] mt-1">
          Predict which thumbnail achieved a statistically significantly higher Click-Through Rate (CTR).
        </p>
      </div>

      {/* Side-by-side (desktop) / Stacked (mobile) Comparison Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Variant A Card */}
        <div
          onClick={() => handleSelect('A')}
          role="button"
          tabIndex={0}
          onKeyDown={(e) => {
            if (e.key === 'Enter' || e.key === ' ') {
              e.preventDefault();
              handleSelect('A');
            }
          }}
          className={`group relative flex flex-col justify-between border rounded-xl p-4 md:p-5 transition-all duration-200 cursor-pointer select-none ${
            selectedVariant === 'A'
              ? 'border-amber-400 bg-[#202025] ring-2 ring-amber-400/40 shadow-lg'
              : 'border-[#27272a] bg-[#18181b] hover:border-neutral-500 hover:bg-[#1e1e22]'
          } ${disabled || isSubmitting ? 'pointer-events-none opacity-80' : ''}`}
        >
          {/* Header pill & keyboard badge */}
          <div className="flex items-center justify-between mb-3">
            <div className="flex items-center space-x-2">
              <span className="text-xs font-bold px-2.5 py-1 rounded bg-amber-500/20 text-amber-300 border border-amber-500/30">
                OPTION A
              </span>
              <span className="text-xs text-[#a1a1aa]">Candidate Variant</span>
            </div>
            <div className="flex items-center space-x-1 text-[11px] font-mono text-[#a1a1aa] bg-[#121212] border border-[#27272a] px-2 py-0.5 rounded">
              <span>Press</span>
              <kbd className="px-1 py-0.2 rounded bg-[#27272a] text-[#f4f4f5] font-bold">1</kbd>
              <span>or</span>
              <kbd className="px-1 py-0.2 rounded bg-[#27272a] text-[#f4f4f5] font-bold">A</kbd>
            </div>
          </div>

          {/* Thumbnail Container */}
          <div className="aspect-video w-full rounded-lg bg-[#121212] border border-[#27272a] overflow-hidden flex items-center justify-center relative mb-4 group-hover:border-neutral-500 transition-colors">
            {!imgAError ? (
              <img
                src={thumbnailAUrl}
                alt={`${title} - Variant A`}
                onError={() => setImgAError(true)}
                className="w-full h-full object-cover group-hover:scale-[1.02] transition-transform duration-300"
              />
            ) : (
              <div className="flex flex-col items-center justify-center text-neutral-500 space-y-2 p-4 text-center">
                <ImageIcon className="w-8 h-8 text-neutral-600" />
                <span className="text-xs font-mono">Thumbnail A Preview</span>
              </div>
            )}

            {/* Selection indicator overlay */}
            {selectedVariant === 'A' && (
              <div className="absolute inset-0 bg-amber-500/10 backdrop-blur-[1px] flex items-center justify-center">
                <div className="bg-amber-400 text-black font-bold px-4 py-2 rounded-lg flex items-center space-x-2 shadow-lg">
                  <Check className="w-5 h-5 stroke-[3]" />
                  <span>Selected Option A</span>
                </div>
              </div>
            )}
          </div>

          {/* Action Button */}
          <button
            type="button"
            onClick={(e) => {
              e.stopPropagation();
              handleSelect('A');
            }}
            disabled={disabled || isSubmitting}
            className={`w-full py-2.5 px-4 rounded-lg font-semibold text-sm transition-all duration-150 flex items-center justify-center space-x-2 ${
              selectedVariant === 'A'
                ? 'bg-amber-400 text-black shadow-md'
                : 'bg-[#222226] text-[#f4f4f5] hover:bg-amber-400 hover:text-black border border-[#27272a]'
            }`}
          >
            <span>Choose Option A</span>
            <span className="text-xs opacity-75 font-mono">[ 1 / A ]</span>
          </button>
        </div>

        {/* Variant B Card */}
        <div
          onClick={() => handleSelect('B')}
          role="button"
          tabIndex={0}
          onKeyDown={(e) => {
            if (e.key === 'Enter' || e.key === ' ') {
              e.preventDefault();
              handleSelect('B');
            }
          }}
          className={`group relative flex flex-col justify-between border rounded-xl p-4 md:p-5 transition-all duration-200 cursor-pointer select-none ${
            selectedVariant === 'B'
              ? 'border-blue-400 bg-[#202025] ring-2 ring-blue-400/40 shadow-lg'
              : 'border-[#27272a] bg-[#18181b] hover:border-neutral-500 hover:bg-[#1e1e22]'
          } ${disabled || isSubmitting ? 'pointer-events-none opacity-80' : ''}`}
        >
          {/* Header pill & keyboard badge */}
          <div className="flex items-center justify-between mb-3">
            <div className="flex items-center space-x-2">
              <span className="text-xs font-bold px-2.5 py-1 rounded bg-blue-500/20 text-blue-300 border border-blue-500/30">
                OPTION B
              </span>
              <span className="text-xs text-[#a1a1aa]">Challenger Variant</span>
            </div>
            <div className="flex items-center space-x-1 text-[11px] font-mono text-[#a1a1aa] bg-[#121212] border border-[#27272a] px-2 py-0.5 rounded">
              <span>Press</span>
              <kbd className="px-1 py-0.2 rounded bg-[#27272a] text-[#f4f4f5] font-bold">2</kbd>
              <span>or</span>
              <kbd className="px-1 py-0.2 rounded bg-[#27272a] text-[#f4f4f5] font-bold">B</kbd>
            </div>
          </div>

          {/* Thumbnail Container */}
          <div className="aspect-video w-full rounded-lg bg-[#121212] border border-[#27272a] overflow-hidden flex items-center justify-center relative mb-4 group-hover:border-neutral-500 transition-colors">
            {!imgBError ? (
              <img
                src={thumbnailBUrl}
                alt={`${title} - Variant B`}
                onError={() => setImgBError(true)}
                className="w-full h-full object-cover group-hover:scale-[1.02] transition-transform duration-300"
              />
            ) : (
              <div className="flex flex-col items-center justify-center text-neutral-500 space-y-2 p-4 text-center">
                <ImageIcon className="w-8 h-8 text-neutral-600" />
                <span className="text-xs font-mono">Thumbnail B Preview</span>
              </div>
            )}

            {/* Selection indicator overlay */}
            {selectedVariant === 'B' && (
              <div className="absolute inset-0 bg-blue-500/10 backdrop-blur-[1px] flex items-center justify-center">
                <div className="bg-blue-400 text-black font-bold px-4 py-2 rounded-lg flex items-center space-x-2 shadow-lg">
                  <Check className="w-5 h-5 stroke-[3]" />
                  <span>Selected Option B</span>
                </div>
              </div>
            )}
          </div>

          {/* Action Button */}
          <button
            type="button"
            onClick={(e) => {
              e.stopPropagation();
              handleSelect('B');
            }}
            disabled={disabled || isSubmitting}
            className={`w-full py-2.5 px-4 rounded-lg font-semibold text-sm transition-all duration-150 flex items-center justify-center space-x-2 ${
              selectedVariant === 'B'
                ? 'bg-blue-400 text-black shadow-md'
                : 'bg-[#222226] text-[#f4f4f5] hover:bg-blue-400 hover:text-black border border-[#27272a]'
            }`}
          >
            <span>Choose Option B</span>
            <span className="text-xs opacity-75 font-mono">[ 2 / B ]</span>
          </button>
        </div>
      </div>
    </div>
  );
};

export default ChallengeCard;
