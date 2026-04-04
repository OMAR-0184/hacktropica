import { LandingHero } from './LandingHero';
import { BentoGrid } from './BentoGrid';
import { HowItWorks } from './HowItWorks';
import { FeatureShowcase } from './FeatureShowcase';

interface LandingPageProps {
  onGetStarted: () => void;
}

export function LandingPage({ onGetStarted }: LandingPageProps) {
  return (
    <div className="flex flex-col w-full min-h-screen relative z-10 w-full overflow-y-auto">
      <LandingHero onGetStarted={onGetStarted} />
      <BentoGrid />
      <FeatureShowcase />
      <HowItWorks />
      
      {/* ── Footer ── */}
      <footer className="w-full py-12 border-t border-white/5 mt-12 bg-background/50 backdrop-blur-md z-20">
        <div className="max-w-6xl mx-auto px-4 flex flex-col md:flex-row justify-between items-center gap-6">
          <div className="flex flex-col items-center md:items-start">
            <span className="text-xl font-bold tracking-tighter text-white">Cogni<span className="text-primary-400">map</span></span>
            <span className="text-gray-500 text-sm mt-1">The Adaptive Learning Interface.</span>
          </div>
          <div className="flex gap-8 text-sm font-medium text-gray-400">
            <a href="#api" className="hover:text-primary-400 transition-colors">API Docs</a>
            <a href="#arch" className="hover:text-primary-400 transition-colors">LangGraph Architecture</a>
            <a href="#oss" className="hover:text-primary-400 transition-colors">Open Source</a>
          </div>
        </div>
      </footer>
    </div>
  );
}
