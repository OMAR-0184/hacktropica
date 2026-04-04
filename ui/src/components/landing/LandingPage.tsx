import React from 'react';
import { LandingHero } from './LandingHero';
import { BentoGrid } from './BentoGrid';
import { HowItWorks } from './HowItWorks';

interface LandingPageProps {
  onGetStarted: () => void;
}

export function LandingPage({ onGetStarted }: LandingPageProps) {
  return (
    <div className="flex flex-col w-full min-h-screen relative z-10 w-full overflow-y-auto">
      <LandingHero onGetStarted={onGetStarted} />
      <BentoGrid />
      <HowItWorks />
      
      {/* ── Footer ── */}
      <footer className="w-full py-8 text-center text-gray-600 text-sm border-t border-border mt-12 bg-background/50 backdrop-blur-sm z-20">
        <p>&copy; {new Date().getFullYear()} Cognimap. Powered by LangGraph.</p>
      </footer>
    </div>
  );
}
