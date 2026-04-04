import { Activity, GitBranch, Target, Zap, ServerCrash } from 'lucide-react';

export function BentoGrid() {
  return (
    <section className="relative z-10 w-full max-w-7xl mx-auto px-4 py-24">
      {/* Grid Background Accents */}
      <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_center,rgba(14,165,233,0.03),transparent_70%)] pointer-events-none" />

      <div className="text-center mb-16 animate-fade-up">
        <h2 className="text-3xl md:text-5xl font-bold text-white mb-5 tracking-tight">Backend states, <span className="text-transparent bg-clip-text bg-gradient-to-r from-primary-400 to-purple-400">visualized.</span></h2>
        <p className="text-lg text-gray-400 max-w-2xl mx-auto font-light">
          Cognimap exposes its complex LangGraph orchestration directly to the frontend, giving you ultimate transparency and control.
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6 lg:gap-8">
        
        {/* ── Widget 1: Live State ── */}
        <div className="tilt-card glass-panel group relative overflow-hidden p-8 flex flex-col justify-between min-h-[360px]">
          {/* Subtle Hover Gradient */}
          <div className="absolute inset-0 bg-gradient-to-br from-primary-500/0 md:group-hover:from-primary-500/5 to-transparent transition-colors duration-500" />
          
          <div className="relative z-10">
            <div className="flex items-center gap-4 mb-5">
              <div className="w-12 h-12 rounded-2xl bg-surface-2 border border-white/10 flex items-center justify-center shadow-lg group-hover:bg-primary-500/10 group-hover:border-primary-500/30 transition-all">
                <Activity className="w-6 h-6 text-primary-400 group-hover:animate-pulse" />
              </div>
              <h3 className="text-lg font-bold text-white tracking-wide">Live State Sync</h3>
            </div>
            <p className="text-gray-400 text-sm mb-8 leading-relaxed">Constant WebSocket monitoring of the background orchestration engine.</p>
          </div>
          
          <div className="relative z-10 bg-[#080c12] border border-white/10 rounded-xl p-5 shadow-inner overflow-hidden font-mono text-[13px] leading-loose group-hover:border-primary-500/30 transition-colors">
            <div className="absolute top-0 left-0 w-[3px] h-full bg-gradient-to-b from-primary-400 to-primary-600 animate-pulse" />
            <pre className="text-gray-300">
              <span className="text-purple-400">"status"</span>: <span className="text-green-400">"ready"</span>,<br/>
              <span className="text-purple-400">"current_phase"</span>: <span className="text-green-400">"lesson"</span>,<br/>
              <span className="text-purple-400">"topic"</span>: <span className="text-yellow-200">"ML Basics"</span><br/>
              <span className="animate-pulse font-bold text-primary-400">_</span>
            </pre>
          </div>
        </div>

        {/* ── Widget 2: Pathfinder (Spans 2 columns on lg) ── */}
        <div className="tilt-card glass-panel group relative overflow-hidden p-8 flex flex-col justify-between min-h-[360px] lg:col-span-2">
          {/* Subtle Hover Gradient */}
          <div className="absolute inset-0 bg-gradient-to-br from-purple-500/0 md:group-hover:from-purple-500/5 to-transparent transition-colors duration-500" />
          
          <div className="relative z-10 flex flex-col md:flex-row md:items-end justify-between mb-8 gap-4">
            <div>
              <div className="flex items-center gap-4 mb-5">
                <div className="w-12 h-12 rounded-2xl bg-surface-2 border border-white/10 flex items-center justify-center shadow-lg group-hover:bg-purple-500/10 group-hover:border-purple-500/30 transition-all">
                  <GitBranch className="w-6 h-6 text-purple-400" />
                </div>
                <h3 className="text-lg font-bold text-white tracking-wide">Hyper-Personalized Path</h3>
              </div>
              <p className="text-gray-400 text-sm leading-relaxed max-w-sm">Dynamic graph branching based on your historical priority and mastery. The engine always knows exactly where you should go next.</p>
            </div>
            <div className="glass-panel border-white/10 px-4 py-2 rounded-lg text-xs font-semibold text-gray-300 flex items-center gap-2">
               <ServerCrash className="w-4 h-4 text-gray-500" />
               Traversal Mode: DFS
            </div>
          </div>
          
          <div className="relative z-10 grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="flex flex-col justify-center bg-surface-2/40 border border-white/5 rounded-xl p-5 hover:bg-surface-2/80 transition-colors cursor-pointer">
              <span className="text-sm font-semibold text-gray-300">Option A</span>
              <span className="text-lg text-white font-bold mt-1">Neural Networks</span>
            </div>
            
            {/* Recommended Node */}
            <div className="flex flex-col justify-center bg-gradient-to-br from-purple-500/10 to-transparent border border-purple-500/30 rounded-xl p-5 relative overflow-hidden cursor-pointer hover:border-purple-500/60 transition-colors shadow-[0_4px_24px_rgba(168,85,247,0.1)]">
              <div className="absolute right-0 top-0 w-32 h-full bg-gradient-to-l from-purple-500/20 to-transparent pointer-events-none" />
              <div className="flex items-center gap-2 mb-1">
                <Zap className="w-4 h-4 text-purple-400 fill-purple-400 animate-pulse" />
                <span className="text-sm font-bold text-purple-300 uppercase tracking-wider">Recommended</span>
              </div>
              <span className="text-lg text-white font-bold">Model Bias</span>
              <span className="text-xs text-purple-300/70 mt-2 font-medium">Factor: Targets unseen/weaker areas.</span>
            </div>
          </div>
        </div>

        {/* ── Widget 3: Mastery Pulse ── */}
        <div className="tilt-card glass-panel group relative overflow-hidden p-8 flex flex-col md:flex-row lg:flex-col items-center justify-between min-h-[360px] lg:col-span-1 md:col-span-2">
          {/* Subtle Hover Gradient */}
          <div className="absolute inset-0 bg-gradient-to-br from-green-500/0 md:group-hover:from-green-500/5 to-transparent transition-colors duration-500" />
          
          <div className="relative z-10 text-center md:text-left lg:text-center w-full">
            <div className="flex flex-col md:flex-row lg:flex-col items-center gap-4 mb-4 md:mb-0 lg:mb-4">
              <div className="w-12 h-12 rounded-2xl bg-surface-2 border border-white/10 flex items-center justify-center shadow-lg group-hover:bg-green-500/10 group-hover:border-green-500/30 transition-all">
                <Target className="w-6 h-6 text-green-400 group-hover:rotate-90 transition-transform duration-700" />
              </div>
              <h3 className="text-lg font-bold text-white tracking-wide">Mastery Pulse</h3>
            </div>
            <p className="text-gray-400 text-sm leading-relaxed mt-4 md:mt-2 lg:mt-4">Granular performance tracking across the entire evaluated syllabus.</p>
          </div>
          
          <div className="relative z-10 w-40 h-40 flex items-center justify-center shrink-0">
            {/* Background Circle */}
            <svg className="absolute inset-0 w-full h-full transform -rotate-90">
              <circle cx="80" cy="80" r="70" className="stroke-surface-2 fill-none stroke-[10]" />
              <circle 
                cx="80" cy="80" r="70" 
                className="stroke-primary-500 fill-none stroke-[10] transition-all duration-1000 ease-out" 
                strokeDasharray="439.8"
                strokeDashoffset={439.8 - (439.8 * 0.67)} 
                strokeLinecap="round"
                style={{ filter: 'drop-shadow(0 0 8px rgba(14,165,233,0.5))' }}
              />
            </svg>
            <div className="flex flex-col items-center">
              <span className="text-4xl font-extrabold text-white tracking-tighter">67<span className="text-2xl text-primary-400">%</span></span>
              <span className="text-[11px] text-gray-500 uppercase tracking-widest mt-1 font-semibold">Mastered</span>
            </div>
          </div>
        </div>

      </div>
    </section>
  );
}
