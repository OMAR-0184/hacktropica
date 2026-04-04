import { Cpu, ChevronRight, Activity, Zap } from 'lucide-react';

interface LandingHeroProps {
  onGetStarted: () => void;
}

export function LandingHero({ onGetStarted }: LandingHeroProps) {
  return (
    <div className="relative min-h-[90vh] flex flex-col justify-center items-center text-center px-4 overflow-hidden z-10 w-full">
      
      {/* ── Background Floating Accents ── */}
      <div className="absolute top-1/4 left-1/4 w-72 h-72 bg-primary-500/10 rounded-full blur-[100px] pointer-events-none animate-pulse-slow" />
      <div className="absolute bottom-1/4 right-1/4 w-96 h-96 bg-purple-500/10 rounded-full blur-[120px] pointer-events-none" style={{ animation: 'pulse 8s infinite alternate' }} />

      <div className="relative z-10 flex flex-col items-center mt-20">
        {/* ── Callout Badge ── */}
        <div className="group inline-flex items-center gap-3 px-4 py-2 rounded-full bg-surface-2/80 backdrop-blur-md border border-white/10 hover:border-primary-500/30 transition-all cursor-pointer mb-10 animate-fade-up shadow-[0_0_24px_rgba(0,0,0,0.5)]">
          <div className="flex items-center justify-center w-6 h-6 rounded-full bg-primary-500/20">
            <Cpu className="w-3.5 h-3.5 text-primary-400 group-hover:scale-110 transition-transform" />
          </div>
          <span className="text-sm font-medium text-gray-300 group-hover:text-white transition-colors">Powered by Advanced LangGraph Agents</span>
          <ChevronRight className="w-4 h-4 text-gray-500 group-hover:text-primary-400 group-hover:translate-x-1 transition-all" />
        </div>

        {/* ── Headline ── */}
        <h1 className="text-5xl md:text-7xl lg:text-[5.5rem] leading-[1.1] font-extrabold tracking-tight text-white mb-8 max-w-5xl animate-fade-up" style={{ animationDelay: '100ms' }}>
          Stop Learning Linearly.<br />
          <span className="text-transparent bg-clip-text bg-gradient-to-r from-primary-400 via-primary-200 to-purple-400">Master Any Topic.</span>
        </h1>
        
        <p className="text-lg md:text-2xl text-gray-400 font-light max-w-3xl mb-14 animate-fade-up" style={{ animationDelay: '200ms' }}>
          Cognimap dynamically generates a living curriculum, orchestrating your learning journey through real-time state-aware AI and adaptive pathfinding.
        </p>

        {/* ── CTA ── */}
        <div className="flex flex-col sm:flex-row gap-5 w-full sm:w-auto animate-fade-up" style={{ animationDelay: '300ms' }}>
          <button 
            onClick={onGetStarted}
            className="group relative flex items-center justify-center gap-3 px-10 py-5 bg-white text-background rounded-full font-bold text-lg hover:shadow-[0_0_40px_rgba(255,255,255,0.3)] transition-all hover:scale-[1.02] overflow-hidden"
          >
            <div className="absolute inset-0 w-full h-full bg-gradient-to-r from-white to-gray-200 group-hover:opacity-0 transition-opacity" />
            <div className="absolute inset-0 w-full h-full bg-gradient-to-r from-primary-400 to-primary-500 opacity-0 group-hover:opacity-100 transition-opacity" />
            <span className="relative z-10 group-hover:text-white transition-colors">Start Your Journey</span>
            <ChevronRight className="relative z-10 w-5 h-5 group-hover:text-white group-hover:translate-x-1 transition-all" />
          </button>
          <button className="px-10 py-5 rounded-full font-bold text-lg text-white glass-panel border border-white/10 hover:bg-white/5 hover:border-white/20 transition-all">
            Read API Docs
          </button>
        </div>
      </div>

      {/* ── Scaled Knowledge Frontier Visualization ── */}
      <div className="relative w-full max-w-5xl h-[300px] md:h-[400px] mt-24 mb-16 mx-auto animate-fade-up perspective-[2000px]" style={{ animationDelay: '500ms' }}>
        
        {/* Abstract Data Streams (Background of node) */}
        <div className="absolute inset-0 flex items-center justify-center opacity-60">
          <div className="w-[120%] h-full rounded-[100%] border border-primary-500/20 shadow-[0_0_80px_rgba(14,165,233,0.1)] animate-[spin_40s_linear_infinite]" style={{ transform: 'rotateX(75deg)' }} />
          <div className="absolute w-[100%] h-[80%] rounded-[100%] border border-purple-500/20 shadow-[0_0_80px_rgba(168,85,247,0.1)] animate-[spin_30s_linear_infinite_reverse]" style={{ transform: 'rotateX(75deg)' }} />
        </div>

        {/* Central Root Node */}
        <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 z-20 hover:scale-105 transition-transform duration-500 cursor-pointer">
          <div className="relative">
            {/* Core Pulse */}
            <div className="absolute -inset-8 bg-primary-500/20 rounded-full blur-2xl animate-pulse-slow" />
            <div className="absolute -inset-4 bg-primary-400/30 rounded-full blur-xl animate-node-ping" />
            
            {/* Node UI */}
            <div className="relative bg-[#0d1117] border border-primary-500/50 shadow-[0_0_32px_rgba(14,165,233,0.3)] rounded-2xl px-8 py-5 flex items-center gap-4 backdrop-blur-xl">
              <div className="relative flex items-center justify-center w-12 h-12 bg-primary-500/20 rounded-xl border border-primary-500/30">
                <Activity className="w-6 h-6 text-primary-400 animate-pulse" />
              </div>
              <div className="flex flex-col text-left">
                <span className="text-xs font-semibold text-primary-400 tracking-widest uppercase mb-1 drop-shadow-[0_0_8px_rgba(14,165,233,0.8)]">Root Node</span>
                <span className="text-xl font-bold text-white tracking-wide">Intro to Machine Learning</span>
              </div>
              
              {/* Fake UI Badge */}
              <div className="absolute -top-3 -right-3 bg-green-500/10 border border-green-500/30 text-green-400 text-[10px] font-bold px-2 py-1 rounded-md flex items-center gap-1 shadow-[0_0_12px_rgba(34,197,94,0.3)]">
                <Zap className="w-3 h-3 fill-green-400" />
                Live
              </div>
            </div>
          </div>
        </div>

        {/* Outgoing Edge Nodes (Floating around the center) */}
        <div className="absolute top-[10%] left-[8%] z-10 glass-panel border-purple-500/30 px-5 py-3 rounded-xl shadow-[0_0_24px_rgba(168,85,247,0.15)] animate-[pulse_4s_ease-in-out_infinite]">
          <span className="text-sm font-medium text-purple-200">Neural Networks</span>
        </div>

        <div className="absolute bottom-[20%] right-[10%] z-10 glass-panel border-blue-500/30 px-5 py-3 rounded-xl shadow-[0_0_24px_rgba(14,165,233,0.15)] animate-[pulse_5s_ease-in-out_infinite]">
          <span className="text-sm font-medium text-blue-200">Model Bias</span>
        </div>

        {/* SVG Flow Lines */}
        <svg className="absolute inset-0 w-full h-full pointer-events-none opacity-80" viewBox="0 0 1000 400" preserveAspectRatio="none">
          {/* Path to Neural Networks */}
          <path d="M 500 200 C 400 200, 200 150, 150 70" 
                className="stroke-purple-500/50 fill-none" strokeWidth="2" />
          <path d="M 500 200 C 400 200, 200 150, 150 70" 
                className="stroke-purple-300 fill-none animate-stream-flow" strokeWidth="3" strokeDasharray="10 20" style={{ filter: 'drop-shadow(0 0 8px #a855f7)' }} />

          {/* Path to Model Bias */}
          <path d="M 500 200 C 600 200, 800 250, 850 300" 
                className="stroke-primary-500/50 fill-none" strokeWidth="2" />
          <path d="M 500 200 C 600 200, 800 250, 850 300" 
                className="stroke-primary-300 fill-none animate-stream-flow" strokeWidth="3" strokeDasharray="10 20" style={{ filter: 'drop-shadow(0 0 8px #0ea5e9)' }} />
        </svg>

      </div>
    </div>
  );
}
