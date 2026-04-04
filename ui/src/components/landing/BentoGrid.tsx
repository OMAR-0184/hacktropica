import { useState, useEffect } from 'react';
import { Activity, GitBranch, Target, Zap, ServerCrash, Cpu, MousePointer2, CheckCircle2, RotateCcw } from 'lucide-react';

export function BentoGrid() {
  // ── Handlers & Interactive State ──
  const [liveState, setLiveState] = useState<'initializing' | 'running' | 'ready'>('ready');
  const [livePhase, setLivePhase] = useState('lesson');
  
  const [pathSelection, setPathSelection] = useState<'none' | 'A' | 'B'>('none');
  const [remediationState, setRemediationState] = useState<'idle' | 'failed' | 'bridged'>('idle');
  const [mastery, setMastery] = useState(67);

  // Auto-progress webhook simulation
  useEffect(() => {
    if (liveState === 'initializing') {
      const t1 = setTimeout(() => { setLiveState('running'); setLivePhase('evaluator'); }, 1500);
      return () => clearTimeout(t1);
    }
    if (liveState === 'running') {
      const t2 = setTimeout(() => { setLiveState('ready'); setLivePhase('lesson'); }, 1500);
      return () => clearTimeout(t2);
    }
  }, [liveState]);

  const triggerLiveSync = () => {
    if (liveState === 'ready') setLiveState('initializing');
  };

  const simulateFailure = () => {
    setRemediationState('failed');
    setTimeout(() => setRemediationState('bridged'), 1200);
  };

  const increaseMastery = () => {
    setMastery(prev => (prev >= 100 ? 67 : Math.min(prev + 11, 100)));
  };

  return (
    <section className="relative z-10 w-full max-w-7xl mx-auto px-4 py-24">
      {/* Grid Background Accents */}
      <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_center,rgba(14,165,233,0.03),transparent_70%)] pointer-events-none" />

      <div className="text-center mb-16 animate-fade-up">
        <h2 className="text-3xl md:text-5xl font-bold text-white mb-5 tracking-tight flex items-center justify-center gap-3">
          Backend states, <span className="text-transparent bg-clip-text bg-gradient-to-r from-primary-400 to-purple-400">visualized.</span>
        </h2>
        <p className="text-lg text-gray-400 max-w-2xl mx-auto font-light mb-4">
          Cognimap exposes its complex LangGraph orchestration directly to the frontend.
        </p>
        <div className="inline-flex items-center gap-2 bg-primary-500/10 border border-primary-500/20 text-primary-300 px-4 py-2 rounded-full text-sm font-semibold">
          <MousePointer2 className="w-4 h-4 animate-bounce" />
          Click on the widgets below to simulate API interactions.
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6 lg:gap-8">
        
        {/* ── Widget 1: Live State ── */}
        <div 
          onClick={triggerLiveSync}
          className="tilt-card glass-panel group relative overflow-hidden p-8 flex flex-col justify-between min-h-[360px] animate-fade-up cursor-pointer hover:border-primary-500/40" 
          style={{ animationDelay: '100ms' }}
        >
          <div className="absolute inset-0 bg-gradient-to-br from-primary-500/0 md:group-hover:from-primary-500/10 to-transparent transition-colors duration-500" />
          
          <div className="relative z-10">
            <div className="flex items-center justify-between mb-5">
              <div className="flex items-center gap-4">
                <div className={`w-12 h-12 rounded-2xl bg-surface-2 border flex items-center justify-center shadow-lg transition-all ${liveState !== 'ready' ? 'border-primary-500 bg-primary-500/20' : 'border-white/10 group-hover:bg-primary-500/10'}`}>
                  <Activity className={`w-6 h-6 text-primary-400 ${liveState !== 'ready' ? 'animate-spin' : ''}`} />
                </div>
                <h3 className="text-lg font-bold text-white tracking-wide">Live State Sync</h3>
              </div>
            </div>
            <p className="text-gray-400 text-sm mb-6 leading-relaxed">Simulate a websocket `/stream` event triggered by the ARQ workers.</p>
          </div>
          
          <div className="relative z-10 bg-[#080c12] border border-white/10 rounded-xl p-5 shadow-inner overflow-hidden font-mono text-[13px] leading-loose group-hover:border-primary-500/30 transition-colors">
            <div className={`absolute top-0 left-0 w-[3px] h-full transition-colors ${liveState !== 'ready' ? 'bg-yellow-400 animate-pulse' : 'bg-primary-500'}`} />
            <pre className="text-gray-300">
              <span className="text-purple-400">"status"</span>: <span className={liveState === 'ready' ? 'text-green-400' : 'text-yellow-400'}>"{liveState}"</span>,<br/>
              <span className="text-purple-400">"current_phase"</span>: <span className="text-green-400">"{livePhase}"</span>,<br/>
              <span className="text-purple-400">"topic"</span>: <span className="text-yellow-200">"ML Basics"</span><br/>
              <span className="animate-pulse font-bold text-primary-400">_</span>
            </pre>
          </div>
        </div>

        {/* ── Widget 2: Pathfinder ── */}
        <div className="tilt-card glass-panel group relative overflow-hidden p-8 flex flex-col justify-between min-h-[360px] lg:col-span-2 animate-fade-up" style={{ animationDelay: '200ms' }}>
          <div className="absolute inset-0 bg-gradient-to-br from-purple-500/0 md:group-hover:from-purple-500/5 to-transparent transition-colors duration-500" />
          
          <div className="relative z-10 flex flex-col md:flex-row md:items-end justify-between mb-8 gap-4">
            <div>
              <div className="flex items-center gap-4 mb-5">
                <div className="w-12 h-12 rounded-2xl bg-surface-2 border border-white/10 flex items-center justify-center shadow-lg group-hover:bg-purple-500/10 group-hover:border-purple-500/30 transition-all">
                  <GitBranch className="w-6 h-6 text-purple-400" />
                </div>
                <h3 className="text-lg font-bold text-white tracking-wide">Dynamic Graph POST</h3>
              </div>
              <p className="text-gray-400 text-sm leading-relaxed max-w-sm">
                Select an option to simulate a <code className="text-purple-300 bg-purple-500/10 px-1 rounded">/continue</code> payload overriding the recommendations.
              </p>
            </div>
            <div className="glass-panel border-white/10 px-4 py-2 rounded-lg text-xs font-semibold text-gray-300 flex items-center gap-2">
               <ServerCrash className="w-4 h-4 text-gray-500" />
               Traversal Mode: DFS
            </div>
          </div>
          
          <div className="relative z-10 grid grid-cols-1 md:grid-cols-2 gap-4">
            {/* Option A */}
            <div 
              onClick={() => setPathSelection('A')}
              className={`flex flex-col justify-center border rounded-xl p-5 cursor-pointer transition-all ${pathSelection === 'A' ? 'bg-purple-500/20 border-purple-500 shadow-[0_0_24px_rgba(168,85,247,0.3)] shadow-inner' : 'bg-surface-2/40 border-white/5 hover:bg-surface-2/80 hover:border-white/20'} ${pathSelection === 'B' ? 'opacity-40 grayscale' : ''}`}
            >
              <div className="flex items-center justify-between">
                <span className="text-sm font-semibold text-gray-300">Option A</span>
                {pathSelection === 'A' && <CheckCircle2 className="w-5 h-5 text-purple-400" />}
              </div>
              <span className="text-lg text-white font-bold mt-1">Neural Networks</span>
            </div>
            
            {/* Recommended Node (Option B) */}
            <div 
               onClick={() => setPathSelection('B')}
               className={`flex flex-col justify-center rounded-xl p-5 relative overflow-hidden cursor-pointer transition-all border ${pathSelection === 'B' ? 'bg-purple-500/20 border-purple-500 shadow-[0_0_24px_rgba(168,85,247,0.3)] shadow-inner' : 'bg-gradient-to-br from-purple-500/10 to-transparent border-purple-500/30 hover:border-purple-500/60'} ${pathSelection === 'A' ? 'opacity-40 grayscale' : ''}`}
            >
              <div className="absolute right-0 top-0 w-32 h-full bg-gradient-to-l from-purple-500/20 to-transparent pointer-events-none" />
              <div className="flex items-center justify-between mb-1">
                <div className="flex items-center gap-2">
                  <Zap className="w-4 h-4 text-purple-400 fill-purple-400 animate-pulse" />
                  <span className="text-sm font-bold text-purple-300 uppercase tracking-wider">Recommended</span>
                </div>
                {pathSelection === 'B' && <CheckCircle2 className="w-5 h-5 text-purple-400 relative z-10" />}
              </div>
              <span className="text-lg text-white font-bold">Model Bias</span>
              <span className="text-xs text-purple-300/70 mt-2 font-medium">Factor: Targets unseen/weaker areas.</span>
            </div>
          </div>
        </div>

        {/* ── Widget 3: Generative Remediation ── */}
        <div 
          onClick={simulateFailure}
          className="tilt-card glass-panel group relative overflow-hidden p-8 flex flex-col justify-between min-h-[360px] lg:col-span-2 animate-fade-up cursor-pointer hover:border-blue-500/30" 
          style={{ animationDelay: '300ms' }}
        >
          <div className="absolute inset-0 bg-gradient-to-br from-blue-500/0 md:group-hover:from-blue-500/5 to-transparent transition-colors duration-500" />
          
          <div className="relative z-10 flex flex-col md:flex-row md:items-end justify-between mb-8 gap-4">
            <div>
              <div className="flex items-center justify-between mb-5">
                <div className="flex items-center gap-4">
                  <div className="w-12 h-12 rounded-2xl bg-surface-2 border border-white/10 flex items-center justify-center shadow-lg group-hover:bg-blue-500/10 transition-all">
                    <Cpu className="w-6 h-6 text-blue-400" />
                  </div>
                  <h3 className="text-lg font-bold text-white tracking-wide">Generative Remediation</h3>
                </div>
              </div>
              <p className="text-gray-400 text-sm leading-relaxed max-w-sm">Click here to fail an evaluation and watch the Curator agent spin up a unique bridge node.</p>
            </div>
          </div>
          
          <div className={`relative z-10 w-full bg-[#080c12] border border-white/10 rounded-xl p-5 shadow-inner overflow-hidden font-mono text-[13px] leading-loose transition-all ${remediationState !== 'idle' ? 'border-red-500/30' : ''}`}>
            
            {remediationState === 'idle' ? (
              <div className="flex flex-col gap-2 opacity-50">
                <div className="flex items-center gap-2">
                  <CheckCircle2 className="w-4 h-4 text-green-500" />
                  <span className="text-green-400 font-semibold uppercase tracking-wider">Evaluation Passed</span>
                </div>
                <pre className="text-gray-400 italic">No bridge tracking active.</pre>
              </div>
            ) : (
              <>
                <div className="flex items-center gap-2 mb-2">
                  <div className="w-2 h-2 rounded-full bg-red-500 animate-pulse" />
                  <span className="text-red-400 text-xs font-semibold uppercase tracking-wider">Evaluation Failed: Matrix Math</span>
                </div>
                <div className="h-px w-full bg-white/5 my-3" />
                
                {remediationState === 'failed' ? (
                  <div className="flex items-center gap-2 animate-pulse">
                    <Zap className="w-4 h-4 text-blue-400 fill-blue-400" />
                    <span className="text-blue-200">Injecting temporary content node...</span>
                  </div>
                ) : (
                  <>
                    <div className="flex items-center gap-2">
                      <Zap className="w-4 h-4 text-green-400 fill-green-400" />
                      <span className="text-green-200">Bridge Active!</span>
                    </div>
                    <pre className="text-gray-300 mt-2 animate-fade-up">
                      <span className="text-purple-400">"bridge_id"</span>: <span className="text-green-400">"n_2491a"</span>,<br/>
                      <span className="text-purple-400">"type"</span>: <span className="text-yellow-200">"Curator Material"</span>
                    </pre>
                  </>
                )}
              </>
            )}
          </div>
        </div>

        {/* ── Widget 4: Mastery Pulse ── */}
        <div 
          onClick={increaseMastery}
          className="tilt-card glass-panel group relative overflow-hidden p-8 flex flex-col md:flex-row lg:flex-col items-center justify-between min-h-[360px] lg:col-span-1 md:col-span-2 animate-fade-up cursor-pointer hover:border-green-500/40" 
          style={{ animationDelay: '400ms' }}
        >
          <div className="absolute inset-0 bg-gradient-to-br from-green-500/0 md:group-hover:from-green-500/10 to-transparent transition-colors duration-500" />
          
          <div className="relative z-10 text-center md:text-left lg:text-center w-full">
            <div className="flex flex-col md:flex-row lg:flex-col items-center gap-4 mb-4 md:mb-0 lg:mb-4">
              <div className="w-12 h-12 rounded-2xl bg-surface-2 border border-white/10 flex items-center justify-center shadow-lg group-hover:bg-green-500/20 group-hover:border-green-500/50 transition-all">
                <Target className="w-6 h-6 text-green-400" />
              </div>
              <h3 className="text-lg font-bold text-white tracking-wide">Mastery Polling</h3>
            </div>
            <p className="text-gray-400 text-sm leading-relaxed mt-4 md:mt-2 lg:mt-4">Click to simulate fetching the latest `<span className="font-mono text-xs text-white">/progress</span>` payload after evaluation.</p>
          </div>
          
          <div className="relative z-10 w-40 h-40 flex items-center justify-center shrink-0">
            {/* Background Circle */}
            <svg className="absolute inset-0 w-full h-full transform -rotate-90">
              <circle cx="80" cy="80" r="70" className="stroke-surface-2 fill-none stroke-[10]" />
              <circle 
                cx="80" cy="80" r="70" 
                className="stroke-primary-500 fill-none stroke-[10] transition-all duration-1000 ease-out" 
                strokeDasharray="439.8"
                strokeDashoffset={439.8 - (439.8 * (mastery/100))} 
                strokeLinecap="round"
                style={{ filter: mastery >= 100 ? 'drop-shadow(0 0 12px rgba(34,197,94,0.8))' : 'drop-shadow(0 0 8px rgba(14,165,233,0.5))', stroke: mastery >= 100 ? '#4ade80' : '' }}
              />
            </svg>
            <div className="flex flex-col items-center">
              {mastery >= 100 ? (
                 <RotateCcw className="w-8 h-8 text-green-400 mb-1" />
              ) : (
                <>
                  <span className="text-4xl font-extrabold text-white tracking-tighter">{mastery}<span className="text-2xl text-primary-400">%</span></span>
                  <span className="text-[11px] text-gray-500 uppercase tracking-widest mt-1 font-semibold">Mastered</span>
                </>
              )}
            </div>
          </div>
        </div>

      </div>
    </section>
  );
}
