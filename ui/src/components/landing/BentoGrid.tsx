import React from 'react';
import { Activity, GitBranch, Target, Zap } from 'lucide-react';

export function BentoGrid() {
  return (
    <section className="relative z-10 w-full max-w-6xl mx-auto px-4 py-20">
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        
        {/* ── Widget 1: Live State ── */}
        <div className="tilt-card glass-panel p-6 flex flex-col justify-between group">
          <div className="flex items-center gap-3 mb-4">
            <div className="w-10 h-10 rounded-xl bg-surface-2 border border-border flex items-center justify-center group-hover:border-primary-500/50 transition-colors">
              <Activity className="w-5 h-5 text-primary-400 group-hover:text-primary-300" />
            </div>
            <h3 className="text-sm font-semibold text-white tracking-wide uppercase">Live State Sync</h3>
          </div>
          <p className="text-gray-400 text-sm mb-6">Real-time WebSocket monitoring of background LangGraph execution.</p>
          
          <div className="bg-[#0b0f19] border border-border rounded-lg p-4 font-mono text-xs overflow-hidden relative">
            <div className="absolute top-0 left-0 w-1 h-full bg-primary-500 rounded-l-lg animate-pulse" />
            <pre className="text-gray-300">
              <span className="text-purple-400">"status"</span>: <span className="text-green-400">"ready"</span>,<br/>
              <span className="text-purple-400">"current_phase"</span>: <span className="text-green-400">"lesson"</span>,<br/>
              <span className="text-purple-400">"topic"</span>: <span className="text-yellow-200">"Machine Learning"</span><br/>
              <span className="animate-pulse">_</span>
            </pre>
          </div>
        </div>

        {/* ── Widget 2: Pathfinder ── */}
        <div className="tilt-card glass-panel p-6 flex flex-col justify-between group lg:col-span-1 md:col-span-2">
          <div className="flex items-center gap-3 mb-4">
            <div className="w-10 h-10 rounded-xl bg-surface-2 border border-border flex items-center justify-center group-hover:border-purple-500/50 transition-colors">
              <GitBranch className="w-5 h-5 text-purple-400 group-hover:text-purple-300" />
            </div>
            <h3 className="text-sm font-semibold text-white tracking-wide uppercase">Hyper-Personalized Path</h3>
          </div>
          <p className="text-gray-400 text-sm mb-6">Dynamic graph branching based on your historical priority and mastery.</p>
          
          <div className="flex flex-col gap-3">
            <div className="flex items-center justify-between bg-surface-2/50 border border-border rounded-lg p-3">
              <span className="text-sm text-gray-300">Option A: Neural Networks</span>
            </div>
            <div className="flex flex-col gap-2 bg-purple-500/10 border border-purple-500/30 rounded-lg p-3 relative overflow-hidden">
              <div className="absolute right-0 top-0 w-32 h-full bg-gradient-to-l from-purple-500/20 to-transparent pointer-events-none" />
              <div className="flex items-center gap-2">
                <Zap className="w-4 h-4 text-purple-400 fill-purple-400" />
                <span className="text-sm font-medium text-purple-200">Recommended: Model Bias</span>
              </div>
              <span className="text-xs text-purple-300/70">Targets weaker areas (DFS Mode).</span>
            </div>
          </div>
        </div>

        {/* ── Widget 3: Mastery Pulse ── */}
        <div className="tilt-card glass-panel p-6 flex flex-col items-center text-center justify-between group">
          <div className="w-full flex items-center gap-3 mb-4 justify-center">
            <div className="w-10 h-10 rounded-xl bg-surface-2 border border-border flex items-center justify-center group-hover:border-green-500/50 transition-colors">
              <Target className="w-5 h-5 text-green-400 group-hover:text-green-300" />
            </div>
            <h3 className="text-sm font-semibold text-white tracking-wide uppercase">Mastery Pulse</h3>
          </div>
          <p className="text-gray-400 text-sm mb-4">Granular performance tracking to guarantee retention.</p>
          
          <div className="relative w-32 h-32 flex items-center justify-center">
            {/* Background Circle */}
            <svg className="absolute inset-0 w-full h-full transform -rotate-90">
              <circle cx="64" cy="64" r="56" className="stroke-surface-2 fill-none stroke-[8]" />
              <circle 
                cx="64" cy="64" r="56" 
                className="stroke-primary-500 fill-none stroke-[8] transition-all duration-1000 ease-out" 
                strokeDasharray="351.858"
                strokeDashoffset={351.858 - (351.858 * 0.67)} 
                strokeLinecap="round"
                style={{ filter: 'drop-shadow(0 0 6px rgba(14,165,233,0.6))' }}
              />
            </svg>
            <div className="flex flex-col items-center">
              <span className="text-3xl font-bold text-white tracking-tighter">67<span className="text-xl text-primary-400">%</span></span>
              <span className="text-[10px] text-gray-500 uppercase tracking-widest mt-1">Mastered</span>
            </div>
          </div>
        </div>

      </div>
    </section>
  );
}
