import React, { useEffect, useState, useCallback } from 'react';
import { AlertCircle } from 'lucide-react';
import Header from '../components/Header';
import LandingHero from '../components/LandingHero';
import ChallengeCard from '../components/ChallengeCard';
import ReceiptModal from '../components/ReceiptModal';
import Scorecard from '../components/Scorecard';
import apiClient, { ApiError } from '../api/client';
import {
  AttemptReceipt,
  GameSessionResponse,
  NextChallengeResponse,
  ScorecardResponse,
} from '../api/types';

export const GamePage: React.FC = () => {
  const [session, setSession] = useState<GameSessionResponse | null>(null);
  const [challenge, setChallenge] = useState<NextChallengeResponse | null>(null);
  const [lastReceipt, setLastReceipt] = useState<AttemptReceipt | null>(null);
  const [scorecard, setScorecard] = useState<ScorecardResponse | null>(null);
  const [activeView, setActiveView] = useState<'challenge' | 'scorecard'>('challenge');
  const [hasStarted, setHasStarted] = useState<boolean>(false);
  const [isSharedView, setIsSharedView] = useState<boolean>(false);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [isSubmitting, setIsSubmitting] = useState<boolean>(false);
  const [isAdvancing, setIsAdvancing] = useState<boolean>(false);
  const [isResetting, setIsResetting] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  // Fetch session telemetry and active challenge or shared scorecard
  const loadGameData = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      const searchParams = new URLSearchParams(window.location.search);
      const sharedSessionId = searchParams.get('session');
      const viewParam = searchParams.get('view');
      const hasUrlParams = Boolean(sharedSessionId || viewParam === 'scorecard');

      // 1. Shared Scorecard Mode: direct inspect without overwriting active session
      if (sharedSessionId) {
        setIsSharedView(true);
        setHasStarted(true);
        const sc = await apiClient.getScorecard(sharedSessionId);
        setScorecard(sc);
        setActiveView('scorecard');
        setIsLoading(false);
        return;
      }

      setIsSharedView(false);

      // 2. Initialize or retrieve current guest session
      const sessionData = await apiClient.initSession();
      setSession(sessionData);

      // Default hasStarted: true if user has existing attempts or explicit URL params, else false
      if (sessionData.total_attempts > 0 || hasUrlParams) {
        setHasStarted(true);
      } else {
        setHasStarted(false);
      }

      // 3. Fetch next unseen challenge in session
      const nextChallenge = await apiClient.getNextChallenge();
      setChallenge(nextChallenge);
      setLastReceipt(null);

      // 4. If round is completed or explicit view=scorecard parameter is present
      if (nextChallenge.round_completed || viewParam === 'scorecard') {
        try {
          const sc = await apiClient.getScorecard(sessionData.id);
          setScorecard(sc);
          setActiveView('scorecard');
        } catch (scErr) {
          console.warn('Unable to load session scorecard:', scErr);
        }
      } else {
        setActiveView('challenge');
      }
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

      // When round is finished, automatically load and display the Scorecard
      if (nextChallenge.round_completed) {
        const sc = await apiClient.getScorecard();
        setScorecard(sc);
        setActiveView('scorecard');

        // Persist view parameter in URL
        const url = new URL(window.location.href);
        url.searchParams.set('view', 'scorecard');
        window.history.replaceState({}, '', url.toString());
      } else {
        setActiveView('challenge');
      }
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

      // Refresh session state
      const updatedSession = await apiClient.getCurrentSession();
      setSession(updatedSession);

      // Seamlessly retrieve first unseen item of next round
      const nextChallenge = await apiClient.getNextChallenge();
      setChallenge(nextChallenge);
      setLastReceipt(null);
      setScorecard(null);
      setActiveView('challenge');

      // Clear view query param
      const url = new URL(window.location.href);
      url.searchParams.delete('view');
      window.history.replaceState({}, '', url.pathname);
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
      // Cleanly clear lastReceipt, scorecard, and any URL query parameters
      setLastReceipt(null);
      setScorecard(null);
      setIsSharedView(false);
      window.history.replaceState({}, '', window.location.pathname);

      // Await resetSession to unconditionally mint a fresh session
      const newSession = await apiClient.resetSession();
      setSession(newSession);

      // Fetch first challenge of Round 1
      const nextChallenge = await apiClient.getNextChallenge();
      setChallenge(nextChallenge);
      setActiveView('challenge');
      setHasStarted(true);
    } catch (err) {
      const msg = err instanceof ApiError ? err.message : 'Failed to reset benchmark run';
      setError(msg);
    } finally {
      setIsResetting(false);
    }
  };

  // Toggle between challenge mode and scorecard
  const handleToggleView = async (targetView: 'challenge' | 'scorecard') => {
    if (targetView === 'scorecard') {
      setIsLoading(true);
      try {
        const sc = await apiClient.getScorecard();
        setScorecard(sc);
        setActiveView('scorecard');

        const url = new URL(window.location.href);
        url.searchParams.set('view', 'scorecard');
        window.history.replaceState({}, '', url.toString());
      } catch (err) {
        const msg = err instanceof ApiError ? err.message : 'Failed to load scorecard';
        setError(msg);
      } finally {
        setIsLoading(false);
      }
    } else {
      if (challenge?.round_completed && (session?.current_round ?? 1) < 3) {
        await handleAdvanceRound();
        return;
      }
      setActiveView('challenge');
      const url = new URL(window.location.href);
      url.searchParams.delete('view');
      window.history.replaceState({}, '', url.pathname);
    }
  };

  // Current stats values
  const currentRound =
    scorecard?.current_round ?? challenge?.round_number ?? session?.current_round ?? 1;
  const attemptIndex = challenge?.attempt_index ?? session?.round_attempts ?? 1;
  const totalRoundItems = challenge?.total_round_items ?? 10;
  const totalCorrect = scorecard?.correct_attempts ?? session?.correct_attempts ?? 0;
  const totalAttempts = scorecard?.total_attempts ?? session?.total_attempts ?? 0;

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
        currentView={activeView}
        onToggleView={totalAttempts > 0 ? handleToggleView : undefined}
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
              {activeView === 'scorecard'
                ? 'Loading benchmark scorecard...'
                : 'Loading benchmark challenge...'}
            </div>
          </div>
        )}

        {/* VIEW 0: LANDING HERO (WHEN NOT STARTED) */}
        {!isLoading && !hasStarted && (
          <LandingHero onStart={() => setHasStarted(true)} />
        )}

        {/* VIEW 1: SCORECARD VIEW */}
        {!isLoading && hasStarted && activeView === 'scorecard' && (
          scorecard ? (
            <Scorecard
              scorecard={scorecard}
              onAdvanceRound={handleAdvanceRound}
              onResetSession={handleResetSession}
              isAdvancing={isAdvancing}
              isSharedView={isSharedView}
            />
          ) : (
            <div className="w-full max-w-xl mx-auto p-8 rounded-2xl bg-[#18181b] border border-[#27272a] text-center flex flex-col items-center space-y-4">
              <p className="text-sm text-[#a1a1aa]">Scorecard data is not loaded.</p>
              <button
                type="button"
                onClick={() => handleToggleView('scorecard')}
                className="px-4 py-2 rounded-xl bg-amber-400 hover:bg-amber-300 text-neutral-950 font-semibold text-xs transition-colors"
              >
                Load Scorecard
              </button>
            </div>
          )
        )}

        {/* VIEW 2: ACTIVE CHALLENGE SCREEN */}
        {!isLoading && hasStarted && activeView === 'challenge' && challenge && !challenge.round_completed && (
          <div className="w-full flex flex-col space-y-6">
            {/* Ground Truth Receipt Modal & Model Comparison Reveal */}
            {lastReceipt && (
              <ReceiptModal
                receipt={lastReceipt}
                onNext={handleProceedNext}
                isLoadingNext={isLoading}
              />
            )}

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

        {/* VIEW 3: ACTIVE VIEW IS CHALLENGE BUT ROUND IS COMPLETED */}
        {!isLoading && hasStarted && activeView === 'challenge' && challenge && challenge.round_completed && (
          scorecard ? (
            <Scorecard
              scorecard={scorecard}
              onAdvanceRound={handleAdvanceRound}
              onResetSession={handleResetSession}
              isAdvancing={isAdvancing}
              isSharedView={isSharedView}
            />
          ) : (
            <div className="w-full max-w-xl mx-auto p-8 rounded-2xl bg-[#18181b] border border-[#27272a] text-center flex flex-col items-center space-y-5">
              <div className="w-12 h-12 rounded-full bg-amber-400/10 border border-amber-400/20 flex items-center justify-center text-amber-400 font-bold text-lg">
                ✓
              </div>
              <div className="space-y-2">
                <h3 className="text-xl font-bold text-[#f4f4f5]">Round Completed!</h3>
                <p className="text-sm text-[#a1a1aa] leading-relaxed">
                  Round Completed! View your scorecard or advance to the next round.
                </p>
              </div>
              <div className="flex items-center space-x-3 pt-2">
                <button
                  type="button"
                  onClick={() => handleToggleView('scorecard')}
                  className="px-5 py-2.5 rounded-xl bg-amber-400 hover:bg-amber-300 text-neutral-950 font-semibold text-sm transition-colors shadow-lg shadow-amber-400/10"
                >
                  View Scorecard
                </button>
                <button
                  type="button"
                  onClick={handleAdvanceRound}
                  disabled={isAdvancing}
                  className="px-5 py-2.5 rounded-xl bg-[#27272a] hover:bg-[#3f3f46] text-[#f4f4f5] font-semibold text-sm transition-colors disabled:opacity-50"
                >
                  {isAdvancing ? 'Advancing...' : 'Advance Round'}
                </button>
              </div>
            </div>
          )
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
