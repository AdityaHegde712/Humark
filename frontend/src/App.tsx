import { useEffect, useState } from 'react';
import { 
  Trophy, 
  ShieldCheck, 
  Activity, 
  Flame, 
  ArrowRight, 
  Sparkles,
  CheckCircle2,
  AlertCircle
} from 'lucide-react';

interface HealthStatus {
  status: string;
  service: string;
}

export default function App() {
  const [health, setHealth] = useState<HealthStatus | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const checkBackend = async () => {
      try {
        const apiUrl = import.meta.env.VITE_API_URL || 'http://localhost:8000';
        const res = await fetch(`${apiUrl}/health`);
        if (!res.ok) {
          throw new Error(`HTTP error! status: ${res.status}`);
        }
        const data = await res.json();
        setHealth(data);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to reach API');
      } finally {
        setLoading(false);
      }
    };

    checkBackend();
  }, []);

  return (
    <div className="min-h-screen bg-[#121212] text-[#e0e0e0] flex flex-col font-sans selection:bg-neutral-800">
      {/* Header */}
      <header className="border-b border-[#262626] bg-[#121212]/80 backdrop-blur sticky top-0 z-50 px-6 py-4">
        <div className="max-w-6xl mx-auto flex items-center justify-between">
          <div className="flex items-center space-x-3">
            <div className="w-8 h-8 rounded bg-gradient-to-br from-amber-500 to-rose-600 flex items-center justify-center font-bold text-black text-sm">
              H
            </div>
            <div>
              <div className="flex items-center space-x-2">
                <span className="font-semibold text-lg tracking-tight text-white">Humark</span>
                <span className="text-xs px-2 py-0.5 rounded-full border border-[#262626] bg-[#181818] text-neutral-400">
                  v0.1.0
                </span>
              </div>
              <p className="text-xs text-neutral-400">Human vs AI YouTube Thumbnail Benchmark</p>
            </div>
          </div>

          <div className="flex items-center space-x-4">
            <div className="flex items-center space-x-2 text-xs border border-[#262626] px-3 py-1.5 rounded-md bg-[#181818]">
              <span className="text-neutral-400">API Status:</span>
              {loading ? (
                <span className="flex items-center text-neutral-400">
                  <Activity className="w-3.5 h-3.5 animate-spin mr-1 text-neutral-500" /> Connecting...
                </span>
              ) : health ? (
                <span className="flex items-center text-emerald-400 font-medium">
                  <CheckCircle2 className="w-3.5 h-3.5 mr-1 text-emerald-400" /> Operational
                </span>
              ) : (
                <span className="flex items-center text-rose-400 font-medium" title={error || 'Offline'}>
                  <AlertCircle className="w-3.5 h-3.5 mr-1 text-rose-400" /> Disconnected
                </span>
              )}
            </div>

            <div className="flex items-center space-x-2 text-xs border border-[#262626] px-3 py-1.5 rounded-md bg-[#181818]">
              <ShieldCheck className="w-3.5 h-3.5 text-neutral-400" />
              <span className="text-neutral-400">P-Value Gate:</span>
              <span className="text-emerald-400 font-mono">p &lt; 0.05</span>
            </div>
          </div>
        </div>
      </header>

      {/* Main Content Area */}
      <main className="flex-1 max-w-6xl mx-auto w-full px-6 py-8 flex flex-col space-y-8">
        {/* Hero Banner / Round Indicator */}
        <section className="border border-[#262626] bg-[#181818] rounded-xl p-6 relative overflow-hidden">
          <div className="max-w-2xl">
            <div className="flex items-center space-x-2 text-xs font-medium text-amber-400 mb-2">
              <Flame className="w-4 h-4" />
              <span>ROUND 1: THE CHALLENGE</span>
            </div>
            <h1 className="text-2xl font-bold tracking-tight text-white mb-2">
              Can you outperform frontier multimodal AI on YouTube thumbnails?
            </h1>
            <p className="text-sm text-neutral-400 leading-relaxed mb-6">
              Pick the thumbnail that generated a higher Click-Through Rate (CTR) in high-powered A/B split tests
              (N &ge; 20,000, two-tailed z-test p &lt; 0.05). Compare your intuition against GPT-4o, Claude 3.5 Sonnet, and Gemini Pro.
            </p>

            <div className="flex items-center space-x-4">
              <button 
                type="button"
                className="inline-flex items-center space-x-2 px-5 py-2.5 rounded-lg bg-white text-black font-medium text-sm hover:bg-neutral-200 transition-colors"
              >
                <span>Start Challenge (10 Items)</span>
                <ArrowRight className="w-4 h-4" />
              </button>
              <div className="text-xs text-neutral-500">
                ~30 seconds estimated duration
              </div>
            </div>
          </div>
        </section>

        {/* Challenge Preview Skeleton */}
        <section className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {/* Card A Skeleton */}
          <div className="border border-[#262626] bg-[#181818] rounded-xl p-5 hover:border-neutral-700 transition-all cursor-pointer group">
            <div className="flex items-center justify-between mb-3">
              <span className="text-xs font-semibold px-2 py-0.5 rounded bg-neutral-800 text-neutral-300">
                OPTION A
              </span>
              <span className="text-xs text-neutral-500 font-mono">Variant #1</span>
            </div>
            <div className="aspect-video w-full rounded-lg bg-[#202020] border border-[#262626] flex items-center justify-center text-neutral-600 mb-3 group-hover:border-neutral-600 transition-colors">
              <span className="text-xs font-mono">Thumbnail Preview A</span>
            </div>
            <div className="text-sm font-medium text-neutral-300">
              High-CTR Variant Candidate
            </div>
          </div>

          {/* Card B Skeleton */}
          <div className="border border-[#262626] bg-[#181818] rounded-xl p-5 hover:border-neutral-700 transition-all cursor-pointer group">
            <div className="flex items-center justify-between mb-3">
              <span className="text-xs font-semibold px-2 py-0.5 rounded bg-neutral-800 text-neutral-300">
                OPTION B
              </span>
              <span className="text-xs text-neutral-500 font-mono">Variant #2</span>
            </div>
            <div className="aspect-video w-full rounded-lg bg-[#202020] border border-[#262626] flex items-center justify-center text-neutral-600 mb-3 group-hover:border-neutral-600 transition-colors">
              <span className="text-xs font-mono">Thumbnail Preview B</span>
            </div>
            <div className="text-sm font-medium text-neutral-300">
              Challenger Variant Candidate
            </div>
          </div>
        </section>

        {/* Rigor & Stats Overview */}
        <section className="grid grid-cols-1 sm:grid-cols-3 gap-4">
          <div className="border border-[#262626] bg-[#181818] rounded-lg p-4">
            <div className="flex items-center space-x-2 text-xs text-neutral-400 mb-1">
              <Trophy className="w-4 h-4 text-amber-400" />
              <span>Benchmark Standard</span>
            </div>
            <div className="text-lg font-semibold text-white">Wilson 95% CI</div>
            <p className="text-xs text-neutral-500 mt-1">
              Confidence intervals account for binomial uncertainty.
            </p>
          </div>

          <div className="border border-[#262626] bg-[#181818] rounded-lg p-4">
            <div className="flex items-center space-x-2 text-xs text-neutral-400 mb-1">
              <ShieldCheck className="w-4 h-4 text-emerald-400" />
              <span>Anti-Luck Verification</span>
            </div>
            <div className="text-lg font-semibold text-white">&gt; 70% Over 30 Items</div>
            <p className="text-xs text-neutral-500 mt-1">
              Requires 3 full rounds without repeat items to earn badge.
            </p>
          </div>

          <div className="border border-[#262626] bg-[#181818] rounded-lg p-4">
            <div className="flex items-center space-x-2 text-xs text-neutral-400 mb-1">
              <Sparkles className="w-4 h-4 text-blue-400" />
              <span>Model Baselines</span>
            </div>
            <div className="text-lg font-semibold text-white">Pre-computed &amp; Blinded</div>
            <p className="text-xs text-neutral-500 mt-1">
              Revealed strictly on post-selection receipt cards.
            </p>
          </div>
        </section>
      </main>

      {/* Footer */}
      <footer className="border-t border-[#262626] py-6 px-6 text-center text-xs text-neutral-500">
        Humark Evaluation Harness &bull; Monorepo Scaffold Phase 1 &bull; Built with FastAPI &amp; React Vite
      </footer>
    </div>
  );
}
