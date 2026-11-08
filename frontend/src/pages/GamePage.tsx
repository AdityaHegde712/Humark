import React, { useEffect, useState, useCallback } from 'react';
import {
  AlertCircle,
  ArrowRight,
  CheckCircle2,
  XCircle,
  Trophy,
  RefreshCw,
} from 'lucide-react';
import Header from '../components/Header';
import ChallengeCard from '../components/ChallengeCard';
import apiClient, { ApiError } from '../api/client';
import {
  AttemptReceipt,
  GameSessionResponse,
  NextChallengeResponse,
} from '../api/types';

export const GamePage: React.FC = () => {
  const [session, setSession] = useState<GameSessionResponse | null>(null);
  const [challenge, setChallenge] = useState<NextChallengeResponse | null>(null);
  const [lastReceipt, setLastReceipt] = useState<AttemptReceipt | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [isSubmitting, setIsSubmitting] = useState<boolean>(false);
  const [isAdvancing, setIsAdvancing] = useState<boolean>(false);
  const [isResetting, setIsResetting] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  // Fetch session telemetry and active challenge
  const loadGameData = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      // Initialize or retrieve existing session
      const sessionData = await apiClient.initSession();
      setSession(sessionData);

      // Fetch next unseen challenge
      const nextChallenge = await apiClient.getNextChallenge();
      setChallenge(nextChallenge);
      setLastReceipt(null);
    } catch (err) {
      const msg = err instanceof ApiError ? err.message : 'Failed to connect to Humark API';
      setError(msg);
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    loadGameData();
  }, [loadGameData]);

  // Handle user's A/B selection
  const handleSelectVariant = async (variant: 'A' | 'B', latencyMs: number) => {
    if (!challenge || !challenge.id || isSubmitting) return;

    setIsSubmitting(true);
    try {
      const receipt = await apiClient.submitAttempt(challenge.id, variant, latencyMs);
      setLastReceipt(receipt);

      // Refresh session statistics
      const updatedSession = await apiClient.getCurrentSession();
      setSession(updatedSession);
    } catch (err) {
      const msg = err instanceof ApiError ? err.message : 'Failed to record attempt';
      setError(msg);
    } finally {
      setIsSubmitting(false);
    }
  };

  // Proceed to next challenge after viewing decision outcome
  const handleProceedNext = async () => {
    setIsLoading(true);
    setError(null);
    try {
      const nextChallenge = await apiClient.getNextChallenge();
      setChallenge(nextChallenge);
      setLastReceipt(null);
    } catch (err) {
      const msg = err instanceof ApiError ? err.message : 'Failed to retrieve next challenge';
      setError(msg);
    } finally {
      setIsLoading(false);
    }
  };

  // Advance session to the next verification round
  const handleAdvanceRound = async () => {
    setIsAdvancing(true);
    setError(null);
    try {
      await apiClient.advanceRound();
      // Reload game data for new round
      await loadGameData();
    } catch (err) {
      const msg = err instanceof ApiError ? err.message : 'Failed to advance round';
      setError(msg);
    } finally {
      setIsAdvancing(false);
    }
  };

  // Reset benchmark run and start fresh
  const handleResetSession = async () => {
    if (isResetting) return;
    setIsResetting(true);
    setError(null);
    try {
      const newSession = await apiClient.resetSession();
      setSession(newSession);
      const nextChallenge = await apiClient.getNextChallenge();
      setChallenge(nextChallenge);
      setLastReceipt(null);
    } catch (err) {
      const msg = err instanceof ApiError ? err.message : 'Failed to reset benchmark run';
      setError(msg);
    } finally {
      setIsResetting(false);
    }
  };

  // Current stats values
  const currentRound = challenge?.round_number ?? session?.current_round ?? 1;
  const attemptIndex = challenge?.attempt_index ?? session?.round_attempts ?? 1;
  const totalRoundItems = challenge?.total_round_items ?? 10;
  const totalCorrect = session?.correct_attempts ?? 0;
  const totalAttempts = session?.total_attempts ?? 0;

  return (
    <div className="min-h-screen bg-[#121212] text-[#f4f4f5] flex flex-col font-sans selection:bg-neutral-800">
      {/* Shell Header */}
      <Header
        currentRound={currentRound}
        attemptIndex={attemptIndex}
        totalRoundItems={totalRoundItems}
        totalCorrect={totalCorrect}
        totalAttempts={totalAttempts}
        onResetSession={handleResetSession}
        isResetting={isResetting}
      />

      {/* Main Gameplay Shell */}
      <main className="flex-1 max-w-6xl mx-auto w-full px-4 sm:px-6 py-8 flex flex-col items-center justify-center">
        {/* Error Notification Alert */}
        {error && (
          <div className="w-full mb-6 p-4 rounded-xl border border-rose-500/30 bg-rose-500/10 text-rose-300 flex items-center justify-between">
            <div className="flex items-center space-x-3">
              <AlertCircle className="w-5 h-5 text-rose-400 flex-shrink-0" />
              <span className="text-sm font-medium">{error}</span>
            </div>
            <button
              type="button"
              onClick={loadGameData}
              className="text-xs bg-rose-500/20 hover:bg-rose-500/30 px-3 py-1.5 rounded-md font-semibold text-rose-200 transition-colors"
            >
              Retry
            </button>
          </div>
        )}

        {/* Loading Spinner State */}
        {isLoading && (
          <div className="flex flex-col items-center justify-center py-20 space-y-4">
            <div className="w-10 h-10 border-2 border-amber-400 border-t-transparent rounded-full animate-spin" />
            <div className="text-sm text-[#a1a1aa] font-medium tracking-wide">
              Loading benchmark challenge...
            </div>
          </div>
        )}

        {/* Round Completed / Exhausted State */}
        {!isLoading && challenge && challenge.round_completed && (
          <div className="w-full max-w-xl mx-auto border border-[#27272a] bg-[#18181b] rounded-2xl p-8 text-center space-y-6 shadow-xl">
            <div className="w-14 h-14 rounded-2xl bg-amber-500/10 border border-amber-500/20 flex items-center justify-center mx-auto text-amber-400">
              <Trophy className="w-7 h-7" />
            </div>

            <div>
              <div className="text-xs font-mono uppercase tracking-widest text-amber-400 mb-1">
                Round {currentRound} Complete
              </div>
              <h2 className="text-2xl font-bold text-[#f4f4f5]">
                {currentRound >= 3
                  ? 'Verification Benchmark Finalized'
                  : `Ready for Round ${currentRound + 1}`}
              </h2>
              <p className="text-sm text-[#a1a1aa] mt-2 leading-relaxed">
                {currentRound >= 3
                  ? 'You have evaluated all 30 unseen thumbnail split tests. Your tamper-evident verification receipt is ready.'
                  : `You evaluated 10 items in Round ${currentRound}. Continue to the next verification round without repeat challenges.`}
              </p>
            </div>

            {/* Score Summary Card */}
            <div className="grid grid-cols-2 gap-4 border border-[#27272a] bg-[#121212] rounded-xl p-4">
              <div>
                <div className="text-xs text-[#a1a1aa]">Round Score</div>
                <div className="text-xl font-bold font-mono text-[#f4f4f5] mt-0.5">
                  {totalCorrect} / {totalAttempts}
                </div>
              </div>
              <div>
                <div className="text-xs text-[#a1a1aa]">Accuracy</div>
                <div className="text-xl font-bold font-mono text-emerald-400 mt-0.5">
                  {totalAttempts > 0 ? ((totalCorrect / totalAttempts) * 100).toFixed(1) : 0}%
                </div>
              </div>
            </div>

            {/* Advance or Scorecard Action */}
            <div className="flex flex-col sm:flex-row gap-3 pt-2">
              {currentRound < 3 ? (
                <button
                  type="button"
                  onClick={handleAdvanceRound}
                  disabled={isAdvancing}
                  className="flex-1 py-3 px-5 rounded-lg bg-white hover:bg-neutral-200 text-black font-semibold text-sm transition-colors flex items-center justify-center space-x-2 disabled:opacity-50"
                >
                  <span>{isAdvancing ? 'Advancing...' : `Advance to Round ${currentRound + 1}`}</span>
                  <ArrowRight className="w-4 h-4" />
                </button>
              ) : (
                <button
                  type="button"
                  onClick={handleResetSession}
                  className="flex-1 py-3 px-5 rounded-lg bg-amber-400 hover:bg-amber-300 text-black font-semibold text-sm transition-colors flex items-center justify-center space-x-2"
                >
                  <RefreshCw className="w-4 h-4" />
                  <span>Start New Run</span>
                </button>
              )}
            </div>
          </div>
        )}

        {/* Active Challenge Screen */}
        {!isLoading && challenge && !challenge.round_completed && (
          <div className="w-full flex flex-col space-y-6">
            {/* If a decision was just submitted, display receipt transition bar */}
            {lastReceipt ? (
              <div className="w-full max-w-6xl mx-auto border border-[#27272a] bg-[#18181b] rounded-xl p-5 shadow-lg flex flex-col md:flex-row md:items-center md:justify-between gap-4">
                <div className="flex items-center space-x-3">
                  {lastReceipt.is_correct ? (
                    <div className="w-10 h-10 rounded-lg bg-emerald-500/20 border border-emerald-500/30 flex items-center justify-center text-emerald-400 flex-shrink-0">
                      <CheckCircle2 className="w-6 h-6" />
                    </div>
                  ) : (
                    <div className="w-10 h-10 rounded-lg bg-rose-500/20 border border-rose-500/30 flex items-center justify-center text-rose-400 flex-shrink-0">
                      <XCircle className="w-6 h-6" />
                    </div>
                  )}
                  <div>
                    <div className="flex items-center space-x-2">
                      <span className="font-bold text-[#f4f4f5]">
                        {lastReceipt.is_correct ? 'Correct Prediction!' : 'Incorrect Prediction'}
                      </span>
                      <span className="text-xs font-mono px-2 py-0.5 rounded bg-[#121212] border border-[#27272a] text-[#a1a1aa]">
                        Winner: Variant {lastReceipt.winning_variant}
                      </span>
                    </div>
                    <p className="text-xs text-[#a1a1aa] mt-0.5">
                      Variant A CTR: {(lastReceipt.ctr_a * 100).toFixed(2)}% vs Variant B CTR:{' '}
                      {(lastReceipt.ctr_b * 100).toFixed(2)}% (p &lt; {lastReceipt.p_value.toFixed(4)})
                    </p>
                  </div>
                </div>

                <button
                  type="button"
                  onClick={handleProceedNext}
                  className="inline-flex items-center justify-center space-x-2 px-5 py-2.5 rounded-lg bg-amber-400 hover:bg-amber-300 text-black font-semibold text-sm transition-colors shadow-sm self-end md:self-auto"
                >
                  <span>Next Challenge</span>
                  <ArrowRight className="w-4 h-4" />
                </button>
              </div>
            ) : null}

            {/* Challenge Card Presentation */}
            <ChallengeCard
              challengeId={challenge.id || 'default'}
              title={challenge.title || 'YouTube Thumbnail A/B Split Test'}
              category={challenge.category || 'youtube_thumbnails'}
              thumbnailAUrl={challenge.thumbnail_a_url || ''}
              thumbnailBUrl={challenge.thumbnail_b_url || ''}
              onSelect={handleSelectVariant}
              isSubmitting={isSubmitting}
              disabled={lastReceipt !== null}
            />
          </div>
        )}
      </main>

      {/* Footer */}
      <footer className="border-t border-[#27272a] py-5 px-6 text-center text-xs text-[#a1a1aa] bg-[#121212]">
        Humark Benchmark &bull; Dark Minimal Flat Harness &bull; Wilson 95% Confidence Gate
      </footer>
    </div>
  );
};

export default GamePage;
