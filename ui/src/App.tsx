import { useEffect, useState } from 'react';
import { AuthModule }   from './components/AuthModule';
import { GraphCanvas }  from './components/GraphCanvas';
import { LandingPage }  from './components/landing/LandingPage';

function App() {
  const [currentView, setCurrentView] = useState<'landing' | 'auth'>('landing');

  useEffect(() => {
    // Handle token from OAuth redirect query param
    const params = new URLSearchParams(window.location.search);
    const token  = params.get('token');
    if (token) {
      localStorage.setItem('hacktropica_token', token);
      // Clean the URL then redirect
      window.history.replaceState({}, '', '/');
      window.location.href = '/dashboard';
    }
  }, []);

  return (
    <div className={`min-h-screen bg-background relative overflow-hidden flex flex-col items-center ${currentView === 'auth' ? 'justify-center p-4' : ''}`}>
      {/* ── Interactive graph canvas ── */}
      <GraphCanvas />

      {/* ── Grid overlay ── */}
      <div className="absolute inset-0 graph-bg pointer-events-none" aria-hidden="true" />

      {/* ── Ambient glow spheres ── */}
      <div
        className="absolute top-[-10%] left-[-5%] w-[520px] h-[520px] rounded-full pointer-events-none"
        style={{
          background: 'radial-gradient(circle, rgba(14,165,233,0.07) 0%, transparent 70%)',
          animation: 'glow-pulse 6s ease-in-out infinite',
          filter: 'blur(60px)',
        }}
        aria-hidden="true"
      />
      <div
        className="absolute bottom-[-15%] right-[-8%] w-[560px] h-[560px] rounded-full pointer-events-none"
        style={{
          background: 'radial-gradient(circle, rgba(139,92,246,0.06) 0%, transparent 70%)',
          animation: 'glow-pulse 8s ease-in-out infinite',
          animationDelay: '3s',
          filter: 'blur(70px)',
        }}
        aria-hidden="true"
      />
      <div
        className="absolute top-[40%] right-[10%] w-[280px] h-[280px] rounded-full pointer-events-none"
        style={{
          background: 'radial-gradient(circle, rgba(14,165,233,0.04) 0%, transparent 70%)',
          animation: 'glow-pulse 5s ease-in-out infinite',
          animationDelay: '1.5s',
          filter: 'blur(50px)',
        }}
        aria-hidden="true"
      />

      {/* ── Main content ── */}
      {currentView === 'landing' ? (
        <LandingPage onGetStarted={() => setCurrentView('auth')} />
      ) : (
        <div className="relative z-10 w-full max-w-[420px] animate-fade-up">
          {/* Back button */}
          <button 
            onClick={() => setCurrentView('landing')}
            className="mb-6 flex items-center gap-2 text-sm text-gray-500 hover:text-white transition-colors"
          >
            ← Back to Home
          </button>
          
          <AuthModule />

          {/* ── Footer ── */}
          <p className="mt-6 text-center text-xs text-gray-700">
            By continuing, you agree to Hacktropica's{' '}
            <a href="#terms" className="text-gray-500 hover:text-gray-400 underline underline-offset-2 transition-colors"
              onClick={(e) => e.preventDefault()}>Terms</a>
            {' '}and{' '}
            <a href="#privacy" className="text-gray-500 hover:text-gray-400 underline underline-offset-2 transition-colors"
              onClick={(e) => e.preventDefault()}>Privacy Policy</a>.
          </p>
        </div>
      )}
    </div>
  );
}

export default App;
