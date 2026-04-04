import React from 'react';
import { Cpu, ChevronRight } from 'lucide-react';

interface LandingHeroProps {
  onGetStarted: () => void;
}

export function LandingHero({ onGetStarted }: LandingHeroProps) {
  return (
    <div className="relative pt-32 pb-20 lg:pt-40 lg:pb-28 overflow-hidden z-10 flex flex-col items-center text-center px-4">
      
      {/* ── Callout Badge ── */}
      <div className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full glass-panel border border-primary-500/30 text-primary-400 text-xs font-semibold uppercase tracking-widest mb-8 animate-fade-up">
        <Cpu className="w-4 h-4" />
        <span>Powered by LangGraph</span>
      </div>

      {/* ── Headline ── */}
      <h1 className="text-4xl md:text-6xl lg:text-7xl font-bold tracking-tight text-white mb-6 max-w-4xl animate-fade-up" style={{ animationDelay: '100ms' }}>
        The most intelligent way to master <span className="text-gradient">any topic.</span>
      </h1>
      
      <p className="text-lg md:text-xl text-gray-400 max-w-2xl mb-12 animate-fade-up" style={{ animationDelay: '200ms' }}>
        Driven by state-aware AI. Cognimap dynamically orchestrates your learning journey through real-time graph generation and adaptive evaluation.
      </p>

      {/* ── CTA ── */}
      <div className="flex flex-col sm:flex-row gap-4 w-full sm:w-auto animate-fade-up" style={{ animationDelay: '300ms' }}>
        <button 
          onClick={onGetStarted}
          className="btn-primary px-8 py-4 text-base rounded-2xl group"
        >
          Start Learning
          <ChevronRight className="w-5 h-5 group-hover:translate-x-1 transition-transform" />
        </button>
        <button className="btn-social px-8 py-4 text-base rounded-2xl">
          View Documentation
        </button>
      </div>

      {/* ── Knowledge Frontier Graph Preview ── */}
      <div className="mt-20 relative w-full max-w-3xl h-64 md:h-80 mx-auto animate-fade-up" style={{ animationDelay: '400ms' }}>
        {/* Core Node */}
        <div className="absolute left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2 z-20">
          <div className="relative group cursor-pointer">
            <div className="absolute inset-0 bg-primary-500/20 rounded-full blur-xl group-hover:bg-primary-500/40 transition-colors duration-500" />
            <div className="glass-panel border-primary-500/50 px-6 py-4 flex items-center gap-3">
              <div className="w-3 h-3 rounded-full bg-primary-400 shadow-[0_0_12px_rgba(56,200,239,0.8)]" />
              <span className="font-semibold text-white tracking-wide">Machine Learning</span>
            </div>
          </div>
        </div>

        {/* SVG Flow Lines connecting to invisible nodes to represent catalog branching */}
        <svg viewBox="0 0 800 400" className="absolute inset-0 w-full h-full pointer-events-none" style={{ filter: 'drop-shadow(0 0 8px rgba(14,165,233,0.3))' }}>
          {/* Top Left Path */}
          <path d="M 400 200 Q 200 100 100 50" 
                className="stroke-primary-500/60 fill-none animate-stream-flow" 
                strokeWidth="2" strokeDasharray="6 4" />
          
          {/* Top Right Path */}
          <path d="M 400 200 Q 600 100 700 50" 
                className="stroke-purple-500/60 fill-none animate-stream-flow" 
                strokeWidth="2" strokeDasharray="6 4" style={{ animationDelay: '0.5s' }} />

          {/* Bottom Left Path */}
          <path d="M 400 200 Q 200 300 100 350" 
                className="stroke-primary-500/40 fill-none animate-stream-flow" 
                strokeWidth="2" strokeDasharray="6 4" style={{ animationDelay: '1s' }}/>
                
          {/* Bottom Right Path */}
          <path d="M 400 200 Q 600 300 700 350" 
                className="stroke-purple-500/40 fill-none animate-stream-flow" 
                strokeWidth="2" strokeDasharray="6 4" style={{ animationDelay: '1.5s' }}/>
        </svg>
      </div>
    </div>
  );
}
